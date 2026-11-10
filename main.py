"""
Module: main.py
Phụ trách: Thành viên 5 (Nhóm trưởng / Tích hợp hệ thống)
Nhiệm vụ: Điều phối chế độ Chơi Tự Do (Free Play) và Luyện Tập (Wait Mode -
          chờ người chơi ấn đúng nốt mới chạy tiếp), chỉnh vị trí và độ trong suốt.
"""

import os
import time
import numpy as np
import pygame

from audio_module import init_sound_bank, play_note, update_sustain_channels
from ui_module import (
    PRACTICE_SONGS,
    build_keyboard_layout,
    create_top_buttons,
    get_hovered_key,
    render_freeplay_scene,
)
from utils import detect_chord_name
from vision_module import HandTracker

EARLY_HIT_WINDOW = 0.30  # Cho phép ấn sớm tối đa 0.3 giây trước khi nốt chạm vạch


def main():
    sounds = init_sound_bank()

    win_w, win_h = 1280, 720
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(
        "Virtual Webcam Piano - Free Play & Wait-Mode Practice Studio (C3 -> B4)"
    )
    clock = pygame.time.Clock()

    fonts = (
        pygame.font.SysFont("segoeui", 15, bold=True),
        pygame.font.SysFont("segoeui", 18, bold=True),
        pygame.font.SysFont("segoeui", 26, bold=True),
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    tracker = HandTracker(base_dir, win_w, win_h)
    top_buttons = create_top_buttons()

    # Khởi tạo bàn phím ở vị trí mặc định phía trên màn hình (piano_top=None)
    (
        white_rects,
        black_rects,
        piano_top,
        _,
        white_h,
        pc_key_to_note,
        note_to_pc_label,
    ) = build_keyboard_layout(win_w, win_h, piano_top=None)

    # Cấu hình chế độ Đầu vào & Giao diện
    input_mode = 0  # 0: Webcam + Bàn phím | 1: Chỉ Bàn phím (60FPS) | 2: Chỉ Webcam
    input_mode_names = [
        "Dau vao: Cam + Phim",
        "Dau vao: Chi Phim",
        "Dau vao: Chi Webcam",
    ]
    sustain_on = True
    key_glow_duration = 0.25

    # Thông số độ trong suốt (mặc định 50%) và chế độ chỉnh vị trí đàn
    transparency_pct = 50
    edit_pos_mode = False
    dragging_piano = False
    drag_offset_y = 0

    # Thông số Chế độ chơi: 0 = Chơi Tự Do | 1 = Luyện Tập (Wait Mode)
    play_mode = 0
    current_song_idx = 0
    practice_notes = []
    song_time = 0.0
    score = 0
    combo = 0
    max_combo = 0
    hit_count = 0
    wrong_count = 0
    last_judge = "SAN SANG"

    key_active_until = {}
    active_channels = {}
    held_pc_keys = set()
    floating_particles = []
    note_history = []
    last_vel_pct = 0

    start_time = time.time()
    prev_frame_time = start_time

    def start_practice_song(song_idx):
        """Khởi tạo hoặc đặt lại bài nhạc trong chế độ Luyện tập (Wait Mode)."""
        nonlocal practice_notes, song_time, score, combo, max_combo, hit_count, wrong_count, last_judge
        song_data = PRACTICE_SONGS[song_idx]
        practice_notes = [
            {"time": float(t), "note": n, "status": "pending"}
            for t, n in song_data["notes"]
        ]
        song_time = 0.0
        score = 0
        combo = 0
        max_combo = 0
        hit_count = 0
        wrong_count = 0
        last_judge = "BAT DAU!"

    start_practice_song(current_song_idx)

    def update_piano_position(new_top):
        """Cập nhật lại tọa độ các phím đàn khi thay đổi vị trí dọc."""
        nonlocal white_rects, black_rects, piano_top, white_h
        (
            white_rects,
            black_rects,
            piano_top,
            _,
            white_h,
            _,
            _,
        ) = build_keyboard_layout(win_w, win_h, piano_top=new_top)

    def trigger_piano_key(note_str, volume):
        nonlocal last_vel_pct, score, combo, max_combo, hit_count, wrong_count, last_judge
        play_note(sounds, active_channels, note_str, volume)
        key_active_until[note_str] = time.time() + key_glow_duration
        last_vel_pct = int(round(volume * 100))

        note_history.append(note_str)
        if len(note_history) > 10:
            note_history.pop(0)

        # Kiểm tra nốt nhạc trong Chế độ Luyện tập (Wait Mode)
        if play_mode == 1:
            pending = [
                item for item in practice_notes if item["status"] == "pending"
            ]
            if pending:
                next_note_item = pending[0]
                target_time = next_note_item["time"]
                target_note = next_note_item["note"]

                # Khi nốt đã gần tới vạch nhịp hoặc đang dừng trên vạch nhịp đợi người chơi
                if (target_time - song_time) <= EARLY_HIT_WINDOW:
                    if note_str == target_note:
                        next_note_item["status"] = "hit"
                        hit_count += 1
                        combo += 1
                        max_combo = max(max_combo, combo)
                        score += 100
                        last_judge = f"CHINH XAC! ({note_str})"
                    else:
                        wrong_count += 1
                        combo = 0
                        last_judge = f"SAI NOT! Can bam: {target_note}"

        rect = black_rects.get(note_str) or white_rects.get(note_str)
        if rect:
            p_col = (255, 185, 40) if "#" in note_str else (80, 255, 140)
            if piano_top < win_h // 3:
                floating_particles.append(
                    [rect.centerx, piano_top + white_h + 15, p_col, note_str, 5]
                )
            else:
                floating_particles.append(
                    [rect.centerx, piano_top - 15, p_col, note_str, -5]
                )

    running = True
    while running:
        now = time.time()
        dt = min(0.1, now - prev_frame_time)
        prev_frame_time = now

        hovered_keys = set(held_pc_keys)

        # 1. Xử lý sự kiện Chuột và Bàn phím máy tính
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if top_buttons["mode"].collidepoint(mx, my):
                    play_mode = 1 - play_mode
                    if play_mode == 1:
                        start_practice_song(current_song_idx)
                elif top_buttons["song"].collidepoint(mx, my):
                    current_song_idx = (current_song_idx + 1) % len(PRACTICE_SONGS)
                    play_mode = 1
                    start_practice_song(current_song_idx)
                elif top_buttons["restart"].collidepoint(mx, my):
                    if play_mode == 1:
                        start_practice_song(current_song_idx)
                    else:
                        note_history.clear()
                elif top_buttons["input"].collidepoint(mx, my):
                    input_mode = (input_mode + 1) % 3
                elif top_buttons["sustain"].collidepoint(mx, my):
                    sustain_on = not sustain_on
                elif top_buttons["sens_down"].collidepoint(mx, my):
                    tracker.adjust_sensitivity(-1)
                elif top_buttons["sens_up"].collidepoint(mx, my):
                    tracker.adjust_sensitivity(1)
                elif top_buttons["opac_down"].collidepoint(mx, my):
                    transparency_pct = max(0, transparency_pct - 10)
                elif top_buttons["opac_up"].collidepoint(mx, my):
                    transparency_pct = min(85, transparency_pct + 10)
                elif top_buttons["pos_mode"].collidepoint(mx, my):
                    edit_pos_mode = not edit_pos_mode
                    dragging_piano = False
                elif top_buttons["pos_up"].collidepoint(mx, my):
                    update_piano_position(piano_top - 25)
                elif top_buttons["pos_down"].collidepoint(mx, my):
                    update_piano_position(piano_top + 25)
                else:
                    if edit_pos_mode and (piano_top - 15 <= my <= piano_top + white_h + 15):
                        dragging_piano = True
                        drag_offset_y = my - piano_top
                    elif edit_pos_mode and my > 90:
                        update_piano_position(my - white_h // 2)
                        dragging_piano = True
                        drag_offset_y = white_h // 2
                    else:
                        clicked_note = get_hovered_key(
                            mx, my, black_rects, white_rects
                        )
                        if clicked_note:
                            trigger_piano_key(clicked_note, 0.90)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_piano = False

            elif event.type == pygame.MOUSEMOTION:
                if edit_pos_mode and dragging_piano:
                    _, my = event.pos
                    update_piano_position(my - drag_offset_y)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F1:
                    input_mode = (input_mode + 1) % 3
                elif event.key == pygame.K_F2:
                    edit_pos_mode = not edit_pos_mode
                    dragging_piano = False
                elif event.key == pygame.K_F3:
                    play_mode = 1 - play_mode
                    if play_mode == 1:
                        start_practice_song(current_song_idx)
                elif event.key == pygame.K_F4:
                    current_song_idx = (current_song_idx + 1) % len(PRACTICE_SONGS)
                    play_mode = 1
                    start_practice_song(current_song_idx)
                elif event.key == pygame.K_SPACE:
                    sustain_on = not sustain_on
                elif event.key == pygame.K_LEFTBRACKET:
                    tracker.adjust_sensitivity(-1)
                elif event.key == pygame.K_RIGHTBRACKET:
                    tracker.adjust_sensitivity(1)
                elif event.key == pygame.K_MINUS:
                    transparency_pct = max(0, transparency_pct - 10)
                elif event.key == pygame.K_EQUALS:
                    transparency_pct = min(85, transparency_pct + 10)
                elif event.key == pygame.K_UP:
                    update_piano_position(piano_top - 25)
                elif event.key == pygame.K_DOWN:
                    update_piano_position(piano_top + 25)
                elif event.key == pygame.K_BACKSPACE:
                    if play_mode == 1:
                        start_practice_song(current_song_idx)
                    else:
                        note_history.clear()

                # Nhấn phím đàn bằng bàn phím máy tính
                if input_mode in [0, 1] and event.key in pc_key_to_note:
                    note_str = pc_key_to_note[event.key]
                    if note_str not in held_pc_keys:
                        held_pc_keys.add(note_str)
                        hovered_keys.add(note_str)
                        trigger_piano_key(note_str, 0.90)

            elif event.type == pygame.KEYUP:
                if event.key in pc_key_to_note:
                    held_pc_keys.discard(pc_key_to_note[event.key])

        # 2. Cập nhật tiến trình bài nhạc theo cơ chế Chờ Nốt (Wait Mode)
        song_finished = False
        target_note = None
        is_waiting_note = False

        if play_mode == 1:
            pending = [
                item for item in practice_notes if item["status"] == "pending"
            ]
            if pending:
                next_time = pending[0]["time"]
                target_note = pending[0]["note"]
                if song_time < next_time:
                    song_time = min(next_time, song_time + dt)
                if song_time >= next_time - 0.005:
                    song_time = next_time
                    is_waiting_note = True
            else:
                song_finished = True

        # 3. Xử lý nhận diện thao tác "Nhấn để đánh" từ Webcam
        hand_skeleton_pts = []
        visual_tips = []

        if input_mode in [0, 2]:
            (
                rgb_frame,
                hand_skeleton_pts,
                visual_tips,
                cam_hovered,
                cam_triggered,
            ) = tracker.process_frame(
                now, dt, start_time, black_rects, white_rects, get_hovered_key
            )
            hovered_keys.update(cam_hovered)

            if not (edit_pos_mode and dragging_piano):
                for t_note, vol in cam_triggered.items():
                    trigger_piano_key(t_note, vol)

            if rgb_frame is not None:
                cam_surface = pygame.surfarray.make_surface(
                    np.transpose(rgb_frame, (1, 0, 2))
                )
                screen.blit(cam_surface, (0, 0))
            else:
                screen.fill((18, 22, 34))
        else:
            screen.fill((18, 22, 34))

        # 4. Quản lý ngân vang Sustain và nhận diện Hợp âm đang vang
        update_sustain_channels(
            active_channels, hovered_keys, key_active_until, now, sustain_on
        )
        currently_sounding = {
            k for k, exp_t in key_active_until.items() if exp_t > now
        } | held_pc_keys
        chord_text = detect_chord_name(currently_sounding)

        total_attempts = hit_count + wrong_count
        accuracy = (
            int(round((hit_count / total_attempts) * 100))
            if total_attempts > 0
            else 100
        )

        # 5. Kết xuất giao diện
        state_info = {
            "play_mode": play_mode,
            "song_title": PRACTICE_SONGS[current_song_idx]["title"],
            "song_time": song_time,
            "practice_notes": practice_notes,
            "target_note": target_note,
            "is_waiting_note": is_waiting_note,
            "score": score,
            "combo": combo,
            "max_combo": max_combo,
            "accuracy": accuracy,
            "last_judge": last_judge,
            "song_finished": song_finished,
            "input_mode_name": input_mode_names[input_mode],
            "sustain_on": sustain_on,
            "sens_pct": tracker.get_sensitivity_percent(),
            "transparency_pct": transparency_pct,
            "edit_pos_mode": edit_pos_mode,
            "chord_text": chord_text,
            "last_vel_pct": last_vel_pct,
            "note_history": note_history,
        }

        render_freeplay_scene(
            screen,
            fonts,
            win_w,
            win_h,
            now,
            white_rects,
            black_rects,
            piano_top,
            white_h,
            note_to_pc_label,
            key_active_until,
            hovered_keys,
            floating_particles,
            hand_skeleton_pts,
            visual_tips,
            top_buttons,
            state_info,
        )

        pygame.display.flip()
        clock.tick(60)

    tracker.release()
    pygame.quit()


if __name__ == "__main__":
    main()