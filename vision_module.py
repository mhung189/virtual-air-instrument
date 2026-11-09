"""
Module: vision_module.py
Phụ trách: Thành viên 3
Nhiệm vụ: Nhận diện bàn tay AI MediaPipe và tối ưu hóa thuật toán "Nhấn để đánh".
"""

import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np
from utils import FINGER_PIP_IDS, FINGERTIP_IDS


class HandTracker:
    """Bộ phân tích động học ngón tay với lọc nhiễu EMA và khóa hồi phím cơ học."""

    def __init__(self, base_dir, width=1280, height=720):
        self.width = width
        self.height = height
        self.finger_state = {}
        self.palm_state = {}
        self.last_timestamp_ms = -1

        # Thông số vật lý của thao tác "Nhấn để đánh"
        self.strike_vel_threshold = 140.0  # Ngưỡng vận tốc nhấn (px/s)
        self.max_strike_vel = 500.0        # Vận tốc nhấn đạt 100% lực
        self.release_lift_px = 9.0         # Khoảng nhấc ngón tay (px) để hồi búa đàn
        self.min_retrigger_sec = 0.085     # Thời gian chống rung đúp phím (85ms)
        self.ema_alpha = 0.65              # Hệ số làm mượt tọa độ EMA

        model_path = os.path.join(base_dir, "hand_landmarker.task")
        model_url = (
            "https://storage.googleapis.com/mediapipe-models/"
            "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        )
        if not os.path.exists(model_path):
            print("Đang tải mô hình AI nhận diện bàn tay...")
            urllib.request.urlretrieve(model_url, model_path)

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.65,
            min_hand_presence_confidence=0.65,
            min_tracking_confidence=0.65,
        )
        self.detector = mp_vision.HandLandmarker.create_from_options(options)

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def adjust_sensitivity(self, delta):
        """Tăng/giảm độ nhạy của thao tác nhấn phím."""
        self.strike_vel_threshold = float(
            np.clip(self.strike_vel_threshold - delta * 20.0, 75.0, 260.0)
        )

    def get_sensitivity_percent(self):
        """Trả về độ nhạy theo tỷ lệ phần trăm (%)."""
        return int(
            round((280.0 - self.strike_vel_threshold) / (280.0 - 75.0) * 100)
        )

    def process_frame(
        self, now, dt, start_time, black_rects, white_rects, get_hovered_fn
    ):
        """Xử lý từng khung hình camera và phát hiện thao tác nhấn xuống của 10 ngón tay."""
        if not self.cap.isOpened():
            return None, [], [], set(), {}

        success, frame = self.cap.read()
        if not success:
            return None, [], [], set(), {}

        dt = max(0.008, min(0.1, dt))
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp_ms = int((now - start_time) * 1000)
        if timestamp_ms <= self.last_timestamp_ms:
            timestamp_ms = self.last_timestamp_ms + 1
        self.last_timestamp_ms = timestamp_ms

        detection_result = self.detector.detect_for_video(
            mp_image, timestamp_ms
        )

        hand_skeleton_pts = []
        visual_tips = []
        cam_hovered_keys = set()
        cam_triggered_notes = {}

        if detection_result.hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(
                detection_result.hand_landmarks
            ):
                raw_pts = [
                    (lm.x * self.width, lm.y * self.height)
                    for lm in hand_landmarks
                ]

                if hand_idx < len(detection_result.handedness):
                    hand_cat = detection_result.handedness[hand_idx][
                        0
                    ].category_name
                else:
                    hand_cat = "Hand"
                hand_label = f"{hand_cat}_{hand_idx}"

                # 1. Đo vận tốc dọc của tâm lòng bàn tay để khử nhiễu khi di chuyển cả bàn tay
                palm_y = 0.5 * (raw_pts[0][1] + raw_pts[9][1])
                if hand_label not in self.palm_state:
                    self.palm_state[hand_label] = {"y": palm_y, "vy": 0.0}
                p_state = self.palm_state[hand_label]
                smooth_palm_y = (
                    self.ema_alpha * palm_y
                    + (1.0 - self.ema_alpha) * p_state["y"]
                )
                palm_vy = (smooth_palm_y - p_state["y"]) / dt
                p_state["y"] = smooth_palm_y
                p_state["vy"] = 0.6 * palm_vy + 0.4 * p_state["vy"]

                int_pts = [(int(px), int(py)) for px, py in raw_pts]
                hand_skeleton_pts.append(int_pts)

                # 2. Phân tích chuyển động nhấn độc lập cho từng ngón tay
                for tip_id in FINGERTIP_IDS:
                    raw_x, raw_y = raw_pts[tip_id]
                    pip_y = raw_pts[FINGER_PIP_IDS[tip_id]][1]
                    f_key = (hand_label, tip_id)

                    if f_key not in self.finger_state:
                        self.finger_state[f_key] = {
                            "x": raw_x,
                            "y": raw_y,
                            "vx": 0.0,
                            "vy": 0.0,
                            "flex_dist": raw_y - pip_y,
                            "pressed": False,
                            "lowest_y": raw_y,
                            "last_strike_time": 0.0,
                            "active_key": None,
                        }

                    st = self.finger_state[f_key]

                    sx = (
                        self.ema_alpha * raw_x
                        + (1.0 - self.ema_alpha) * st["x"]
                    )
                    sy = (
                        self.ema_alpha * raw_y
                        + (1.0 - self.ema_alpha) * st["y"]
                    )

                    inst_vx = (sx - st["x"]) / dt
                    inst_vy = (sy - st["y"]) / dt

                    vx = 0.65 * inst_vx + 0.35 * st["vx"]
                    vy = 0.65 * inst_vy + 0.35 * st["vy"]

                    cur_flex = sy - pip_y
                    flex_vy = (cur_flex - st["flex_dist"]) / dt

                    st["x"], st["y"] = sx, sy
                    st["vx"], st["vy"] = vx, vy
                    st["flex_dist"] = cur_flex

                    cx, cy = int(sx), int(sy)
                    target_key = get_hovered_fn(
                        cx, cy, black_rects, white_rects
                    )

                    # Vận tốc nhấn hiệu dụng (kết hợp hạ đầu ngón và gập đốt ngón)
                    net_finger_vy = vy - 0.45 * max(0.0, p_state["vy"])
                    effective_vy = 0.65 * net_finger_vy + 0.35 * max(
                        0.0, flex_vy
                    )

                    # Chống kêu nhầm khi lướt ngang bàn tay
                    is_swiping_sideways = abs(vx) > max(165.0, 1.30 * abs(vy))

                    # Hồi phím cơ học khi nhấc nhẹ ngón tay lên hoặc rời khỏi phím
                    if st["pressed"]:
                        if sy > st["lowest_y"]:
                            st["lowest_y"] = sy
                        if (
                            (st["lowest_y"] - sy) >= self.release_lift_px
                            or vy < -60.0
                            or target_key != st["active_key"]
                        ):
                            st["pressed"] = False
                            st["active_key"] = None

                    # Kích hoạt phát âm khi vận tốc nhấn vượt ngưỡng
                    if target_key is not None:
                        cam_hovered_keys.add(target_key)

                        if (
                            not st["pressed"]
                            and not is_swiping_sideways
                            and effective_vy >= self.strike_vel_threshold
                            and (now - st["last_strike_time"])
                            >= self.min_retrigger_sec
                        ):
                            norm_force = (
                                effective_vy - self.strike_vel_threshold
                            ) / (
                                self.max_strike_vel - self.strike_vel_threshold
                            )
                            volume = float(
                                np.clip(0.40 + 0.60 * norm_force, 0.40, 1.0)
                            )

                            cam_triggered_notes[target_key] = volume
                            st["pressed"] = True
                            st["lowest_y"] = sy
                            st["last_strike_time"] = now
                            st["active_key"] = target_key

                    press_ratio = float(
                        np.clip(
                            effective_vy / self.strike_vel_threshold, 0.0, 1.0
                        )
                    )
                    visual_tips.append(
                        (
                            cx,
                            cy,
                            press_ratio,
                            st["pressed"]
                            or (now - st["last_strike_time"]) < 0.12,
                        )
                    )

        return (
            rgb_frame,
            hand_skeleton_pts,
            visual_tips,
            cam_hovered_keys,
            cam_triggered_notes,
        )

    def release(self):
        """Giải phóng tài nguyên Camera và MediaPipe."""
        self.detector.close()
        self.cap.release()