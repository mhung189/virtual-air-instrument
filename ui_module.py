"""
Module: ui_module.py
Phụ trách: Thành viên 4
Nhiệm vụ: Thiết kế giao diện Chơi Tự Do (Free Play) & Luyện Tập (Wait Mode - Chờ nốt),
          dãn phím 1.5x, chỉnh vị trí đàn và độ trong suốt mặc định 50%.
"""

import pygame
from utils import (
    BLACK_KEY_BINDINGS,
    END_MIDI,
    HAND_CONNECTIONS,
    NOTE_NAMES,
    START_MIDI,
    WHITE_KEY_BINDINGS,
)

HUD_HEIGHT = 90
KEY_SCALE_Y = 1.5  # Hệ số dãn phím theo chiều dọc (1.5 lần)
FALL_SPEED = 165.0  # Tốc độ nốt nhạc rơi xuống (pixels / giây)

# Danh sách các bản nhạc mẫu cho Chế độ Luyện tập: (thời_điểm_giây, tên_nốt)
PRACTICE_SONGS = [
    {
        "title": "Twinkle Star",
        "notes": [
            (1.0, "C4"), (1.6, "C4"), (2.2, "G4"), (2.8, "G4"), (3.4, "A4"), (4.0, "A4"), (4.6, "G4"),
            (5.5, "F4"), (6.1, "F4"), (6.7, "E4"), (7.3, "E4"), (7.9, "D4"), (8.5, "D4"), (9.1, "C4"),
            (10.0, "G4"), (10.6, "G4"), (11.2, "F4"), (11.8, "F4"), (12.4, "E4"), (13.0, "E4"), (13.6, "D4"),
            (14.5, "G4"), (15.1, "G4"), (15.7, "F4"), (16.3, "F4"), (16.9, "E4"), (17.5, "E4"), (18.1, "D4"),
            (19.0, "C4"), (19.6, "C4"), (20.2, "G4"), (20.8, "G4"), (21.4, "A4"), (22.0, "A4"), (22.6, "G4"),
            (23.5, "F4"), (24.1, "F4"), (24.7, "E4"), (25.3, "E4"), (25.9, "D4"), (26.5, "D4"), (27.1, "C4"),
        ],
    },
    {
        "title": "Ode to Joy",
        "notes": [
            (1.0, "E4"), (1.5, "E4"), (2.0, "F4"), (2.5, "G4"), (3.0, "G4"), (3.5, "F4"), (4.0, "E4"), (4.5, "D4"),
            (5.0, "C4"), (5.5, "C4"), (6.0, "D4"), (6.5, "E4"), (7.0, "E4"), (7.7, "D4"), (8.1, "D4"),
            (8.9, "E4"), (9.4, "E4"), (9.9, "F4"), (10.4, "G4"), (10.9, "G4"), (11.4, "F4"), (11.9, "E4"), (12.4, "D4"),
            (12.9, "C4"), (13.4, "C4"), (13.9, "D4"), (14.4, "E4"), (14.9, "D4"), (15.6, "C4"), (16.0, "C4"),
        ],
    },
    {
        "title": "Jingle Bells",
        "notes": [
            (1.0, "E4"), (1.5, "E4"), (2.0, "E4"), (2.8, "E4"), (3.3, "E4"), (3.8, "E4"),
            (4.6, "E4"), (5.1, "G4"), (5.6, "C4"), (6.1, "D4"), (6.6, "E4"),
            (7.5, "F4"), (8.0, "F4"), (8.5, "F4"), (9.0, "F4"), (9.5, "F4"), (10.0, "E4"), (10.5, "E4"), (11.0, "E4"),
            (11.5, "E4"), (12.0, "D4"), (12.5, "D4"), (13.0, "E4"), (13.5, "D4"), (14.3, "G4"),
        ],
    },
    {
        "title": "Happy Birthday",
        "notes": [
            (1.0, "C4"), (1.4, "C4"), (1.9, "D4"), (2.5, "C4"), (3.1, "F4"), (3.7, "E4"),
            (4.6, "C4"), (5.0, "C4"), (5.5, "D4"), (6.1, "C4"), (6.7, "G4"), (7.3, "F4"),
            (8.2, "C4"), (8.6, "C4"), (9.1, "C4"), (9.7, "A4"), (10.3, "F4"), (10.9, "E4"), (11.5, "D4"),
            (12.4, "A#4"), (12.8, "A#4"), (13.3, "A4"), (13.9, "F4"), (14.5, "G4"), (15.1, "F4"),
        ],
    },
]


def build_keyboard_layout(width, height, piano_top=None, scale_y=KEY_SCALE_Y):
    """Tạo tọa độ cho 2 quãng tám (C3 -> B4) với vị trí mặc định ở phía trên và dãn dọc 1.5x."""
    white_notes = []
    black_notes = []

    for midi_num in range(START_MIDI, END_MIDI + 1):
        n_name = NOTE_NAMES[midi_num % 12]
        oct_num = (midi_num // 12) - 1
        full_name = f"{n_name}{oct_num}"
        if "#" in n_name:
            black_notes.append((full_name, midi_num, len(white_notes) - 1))
        else:
            white_notes.append((full_name, midi_num))

    margin_x = 30
    white_h = int(235 * scale_y)  # Dãn chiều dọc 1.5 lần (235 * 1.5 = 352px)
    black_h = int(white_h * 0.60)

    min_top = HUD_HEIGHT + 14
    max_top = max(min_top, height - white_h - 10)

    if piano_top is None:
        piano_top = min_top
    else:
        piano_top = max(min_top, min(int(piano_top), max_top))

    white_w = (width - 2 * margin_x) // len(white_notes)
    black_w = int(white_w * 0.60)

    white_rects = {}
    pc_key_to_note = {}
    note_to_pc_label = {}

    for idx, (full_name, _) in enumerate(white_notes):
        rx1 = margin_x + idx * white_w
        white_rects[full_name] = pygame.Rect(rx1, piano_top, white_w, white_h)
        if idx < len(WHITE_KEY_BINDINGS):
            k_code, k_lbl = WHITE_KEY_BINDINGS[idx]
            pc_key_to_note[k_code] = full_name
            note_to_pc_label[full_name] = k_lbl

    black_rects = {}
    for idx, (full_name, _, left_white_idx) in enumerate(black_notes):
        rx1 = margin_x + (left_white_idx + 1) * white_w - (black_w // 2)
        black_rects[full_name] = pygame.Rect(rx1, piano_top, black_w, black_h)
        if idx < len(BLACK_KEY_BINDINGS):
            k_code, k_lbl = BLACK_KEY_BINDINGS[idx]
            pc_key_to_note[k_code] = full_name
            note_to_pc_label[full_name] = k_lbl

    return (
        white_rects,
        black_rects,
        piano_top,
        white_w,
        white_h,
        pc_key_to_note,
        note_to_pc_label,
    )


def get_hovered_key(px, py, b_rects, w_rects):
    """Kiểm tra tọa độ (px, py) đang nằm trên phím nào (ưu tiên phím đen)."""
    for k_name, rect in b_rects.items():
        if rect.collidepoint(px, py):
            return k_name
    for k_name, rect in w_rects.items():
        if rect.collidepoint(px, py):
            return k_name
    return None


def create_top_buttons():
    """Tạo các nút điều khiển trên thanh Studio HUD."""
    return {
        "mode": pygame.Rect(12, 8, 172, 34),
        "song": pygame.Rect(190, 8, 206, 34),
        "restart": pygame.Rect(402, 8, 94, 34),
        "input": pygame.Rect(502, 8, 196, 34),
        "sustain": pygame.Rect(704, 8, 126, 34),
        "sens_down": pygame.Rect(836, 8, 26, 34),
        "sens_up": pygame.Rect(954, 8, 26, 34),
        "opac_down": pygame.Rect(986, 8, 26, 34),
        "opac_up": pygame.Rect(1114, 8, 26, 34),
        "pos_mode": pygame.Rect(1146, 8, 66, 34),
        "pos_up": pygame.Rect(1216, 8, 26, 34),
        "pos_down": pygame.Rect(1246, 8, 26, 34),
    }


def render_freeplay_scene(
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
):
    """Vẽ giao diện đàn Piano, chế độ Luyện tập (Wait Mode), khung xương tay và HUD."""
    font_sm, font_md, _ = fonts
    is_practice = state_info.get("play_mode", 0) == 1
    target_note = state_info.get("target_note", None)
    is_waiting_note = state_info.get("is_waiting_note", False)

    # 1. Vẽ hiệu ứng bong bóng tên nốt nhạc bay lên/xuống
    new_particles = []
    for item in floating_particles:
        p_x, p_y, p_col, p_lbl, p_vy = item
        if HUD_HEIGHT + 5 < p_y < win_h - 15:
            pygame.draw.circle(screen, p_col, (p_x, p_y), 18)
            pygame.draw.circle(screen, (255, 255, 255), (p_x, p_y), 20, 2)
            t_surf = font_sm.render(p_lbl, True, (15, 15, 20))
            screen.blit(
                t_surf,
                (
                    p_x - t_surf.get_width() // 2,
                    p_y - t_surf.get_height() // 2,
                ),
            )
            new_particles.append([p_x, p_y + p_vy, p_col, p_lbl, p_vy])
    floating_particles[:] = new_particles

    # 2. Vẽ đàn Piano lên một Surface riêng để xử lý độ trong suốt (Transparency)
    piano_surf = pygame.Surface((win_w, win_h))
    colorkey = (1, 2, 3)
    piano_surf.fill(colorkey)
    piano_surf.set_colorkey(colorkey)

    transparency_pct = state_info.get("transparency_pct", 50)
    alpha_val = int(round((100 - transparency_pct) * 2.55))
    piano_surf.set_alpha(alpha_val)

    # Gờ nẹp đàn Piano phía trên bàn phím
    pygame.draw.rect(
        piano_surf,
        (165, 35, 65),
        (30, piano_top - 10, win_w - 60, 10),
        border_radius=3,
    )

    # Vẽ 14 phím trắng
    for name, rect in white_rects.items():
        is_active = key_active_until.get(name, 0) > now
        is_target = is_practice and (name == target_note) and is_waiting_note
        sink_px = 9 if is_active else 0

        if is_active:
            color = (95, 255, 135)
        elif is_target:
            color = (255, 240, 130)  # Làm sáng phím cần bấm khi đang đợi
        elif name in hovered_keys:
            color = (205, 238, 255)
        else:
            color = (246, 246, 250)

        drawn_rect = pygame.Rect(
            rect.left, rect.top + sink_px, rect.width, rect.height - sink_px
        )
        pygame.draw.rect(
            piano_surf,
            color,
            drawn_rect,
            border_bottom_left_radius=6,
            border_bottom_right_radius=6,
        )
        if not is_active:
            pygame.draw.rect(
                piano_surf,
                (175, 180, 190),
                (rect.left, rect.bottom - 14, rect.width, 14),
                border_bottom_left_radius=6,
                border_bottom_right_radius=6,
            )

        border_col = (255, 140, 0) if is_target else (40, 45, 55)
        border_w = 4 if is_target else 2
        pygame.draw.rect(
            piano_surf,
            border_col,
            drawn_rect,
            width=border_w,
            border_bottom_left_radius=6,
            border_bottom_right_radius=6,
        )

        pc_char = note_to_pc_label.get(name, "")
        if pc_char:
            key_badge = pygame.Rect(
                rect.centerx - 15, drawn_rect.bottom - 70, 30, 24
            )
            pygame.draw.rect(
                piano_surf, (45, 55, 75), key_badge, border_radius=5
            )
            k_surf = font_sm.render(pc_char, True, (255, 230, 100))
            piano_surf.blit(
                k_surf,
                (
                    key_badge.centerx - k_surf.get_width() // 2,
                    key_badge.centery - k_surf.get_height() // 2,
                ),
            )

        n_col = (200, 30, 30) if name.startswith("C") else (45, 45, 55)
        n_surf = font_md.render(name, True, n_col)
        piano_surf.blit(
            n_surf,
            (
                rect.centerx - n_surf.get_width() // 2,
                drawn_rect.bottom - 40,
            ),
        )

    # Vẽ 10 phím đen
    for name, rect in black_rects.items():
        is_active = key_active_until.get(name, 0) > now
        is_target = is_practice and (name == target_note) and is_waiting_note
        sink_px = 6 if is_active else 0

        if is_active:
            color = (255, 175, 30)
        elif is_target:
            color = (220, 140, 25)  # Làm sáng phím đen cần bấm khi đang đợi
        elif name in hovered_keys:
            color = (75, 85, 105)
        else:
            color = (28, 30, 38)

        drawn_rect = pygame.Rect(
            rect.left, rect.top + sink_px, rect.width, rect.height - sink_px
        )
        pygame.draw.rect(
            piano_surf,
            color,
            drawn_rect,
            border_bottom_left_radius=5,
            border_bottom_right_radius=5,
        )
        border_col = (255, 240, 100) if is_target else (10, 10, 15)
        border_w = 3 if is_target else 2
        pygame.draw.rect(
            piano_surf,
            border_col,
            drawn_rect,
            width=border_w,
            border_bottom_left_radius=5,
            border_bottom_right_radius=5,
        )

        pc_char = note_to_pc_label.get(name, "")
        if pc_char:
            k_surf = font_sm.render(f"[{pc_char}]", True, (255, 220, 90))
            piano_surf.blit(
                k_surf,
                (
                    rect.centerx - k_surf.get_width() // 2,
                    drawn_rect.bottom - 46,
                ),
            )

        n_surf = font_sm.render(name, True, (220, 225, 235))
        piano_surf.blit(
            n_surf,
            (
                rect.centerx - n_surf.get_width() // 2,
                drawn_rect.bottom - 26,
            ),
        )

    # Hiển thị lớp đàn bán trong suốt lên màn hình
    screen.blit(piano_surf, (0, 0))

    # 3. Vẽ Nốt nhạc rơi xuống & Đợi người chơi ấn (Wait Mode)
    if is_practice:
        song_time = state_info.get("song_time", 0.0)
        practice_notes = state_info.get("practice_notes", [])

        if piano_top < 260:
            hit_y = piano_top + white_h - 45
        else:
            hit_y = piano_top + 15

        # Vẽ Vạch Căn Nhịp (Hit Line)
        line_col = (255, 215, 0) if is_waiting_note else (0, 240, 255)
        pygame.draw.line(
            screen, line_col, (30, hit_y), (win_w - 30, hit_y), 4
        )
        pygame.draw.line(
            screen, (255, 255, 255), (30, hit_y), (win_w - 30, hit_y), 1
        )

        if is_waiting_note and target_note:
            pc_lbl = note_to_pc_label.get(target_note, "")
            wait_str = f"DANG CHO BAM NOT: {target_note} (Phim [{pc_lbl}])"
            hit_lbl = font_sm.render(wait_str, True, (255, 235, 80))
        else:
            hit_lbl = font_sm.render("VACH NHIP (WAIT MODE)", True, (0, 240, 255))
        screen.blit(hit_lbl, (35, hit_y - 24))

        note_bar_h = 36
        for item in practice_notes:
            if item["status"] != "pending":
                continue

            n_name = item["note"]
            n_time = item["time"]

            # Tọa độ đáy của thanh nốt (dừng ngay tại hit_y khi tới lượt)
            note_bottom_y = int(hit_y - max(0.0, n_time - song_time) * FALL_SPEED)
            note_top_y = note_bottom_y - note_bar_h

            if note_bottom_y < HUD_HEIGHT or note_top_y > win_h:
                continue

            key_rect = black_rects.get(n_name) or white_rects.get(n_name)
            if not key_rect:
                continue

            bar_w = max(34, key_rect.width - 8)
            bar_rect = pygame.Rect(
                key_rect.centerx - bar_w // 2,
                note_top_y,
                bar_w,
                note_bar_h,
            )

            is_current_wait = is_waiting_note and abs(n_time - song_time) < 0.01
            if is_current_wait:
                bg_col = (255, 225, 45)
                border_col = (255, 60, 60)
                b_width = 3
            else:
                bg_col = (255, 165, 35) if "#" in n_name else (45, 195, 255)
                border_col = (255, 255, 255)
                b_width = 2

            pygame.draw.rect(screen, bg_col, bar_rect, border_radius=7)
            pygame.draw.rect(
                screen, border_col, bar_rect, width=b_width, border_radius=7
            )

            pc_lbl = note_to_pc_label.get(n_name, "")
            bar_text = f"{n_name} [{pc_lbl}]" if pc_lbl else n_name
            txt_surf = font_sm.render(bar_text, True, (15, 20, 30))
            screen.blit(
                txt_surf,
                (
                    bar_rect.centerx - txt_surf.get_width() // 2,
                    bar_rect.centery - txt_surf.get_height() // 2,
                ),
            )

        # Thông báo khi hoàn thành bài nhạc
        if state_info.get("song_finished", False):
            done_rect = pygame.Rect(win_w // 2 - 230, win_h - 110, 460, 75)
            pygame.draw.rect(screen, (18, 28, 45), done_rect, border_radius=10)
            pygame.draw.rect(
                screen, (80, 255, 160), done_rect, width=2, border_radius=10
            )
            t1 = font_md.render(
                f"HOAN THANH BAI NHAC! Diem: {state_info['score']} | Chinh xac: {state_info['accuracy']}%",
                True,
                (100, 255, 170),
            )
            t2 = font_sm.render(
                "Click 'Reset [R]' hoac nhan [Backspace] de choi lai  |  Nhan [F4] de doi bai",
                True,
                (220, 235, 255),
            )
            screen.blit(t1, (done_rect.centerx - t1.get_width() // 2, done_rect.top + 12))
            screen.blit(t2, (done_rect.centerx - t2.get_width() // 2, done_rect.top + 42))

    # Khung viền báo hiệu khi đang bật Chế độ chỉnh vị trí đàn
    if state_info.get("edit_pos_mode", False):
        outline_rect = pygame.Rect(28, piano_top - 12, win_w - 56, white_h + 14)
        pygame.draw.rect(
            screen, (0, 230, 255), outline_rect, width=3, border_radius=6
        )
        banner_rect = pygame.Rect(
            win_w // 2 - 250, piano_top + white_h // 2 - 20, 500, 40
        )
        pygame.draw.rect(screen, (15, 25, 40), banner_rect, border_radius=8)
        pygame.draw.rect(
            screen, (0, 230, 255), banner_rect, width=2, border_radius=8
        )
        msg_surf = font_sm.render(
            "CHE DO CHINH VI TRI: Keo chuot tren dan hoac nhan mui ten LEN/XUONG",
            True,
            (100, 255, 230),
        )
        screen.blit(
            msg_surf,
            (
                banner_rect.centerx - msg_surf.get_width() // 2,
                banner_rect.centery - msg_surf.get_height() // 2,
            ),
        )

    # 4. Vẽ khung xương bàn tay và vòng đo lực nhấn trên từng đầu ngón tay
    for pts in hand_skeleton_pts:
        for p1, p2 in HAND_CONNECTIONS:
            pygame.draw.line(screen, (220, 235, 245), pts[p1], pts[p2], 2)
        for px, py in pts:
            pygame.draw.circle(screen, (255, 140, 40), (px, py), 4)

    for cx, cy, press_ratio, is_pressed in visual_tips:
        if is_pressed:
            pygame.draw.circle(screen, (50, 255, 110), (cx, cy), 16)
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 19, 3)
        else:
            inner_r = int(6 + 8 * press_ratio)
            pygame.draw.circle(screen, (255, 215, 50), (cx, cy), inner_r)
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 14, 2)

    # 5. Vẽ Thanh Studio HUD ở cạnh trên
    pygame.draw.rect(screen, (15, 20, 32), (0, 0, win_w, HUD_HEIGHT))
    pygame.draw.line(
        screen, (65, 80, 110), (0, HUD_HEIGHT), (win_w, HUD_HEIGHT), 2
    )

    def draw_ui_button(rect, text, bg_col, active=False):
        col = (45, 135, 220) if active else bg_col
        pygame.draw.rect(screen, col, rect, border_radius=7)
        pygame.draw.rect(
            screen, (140, 165, 200), rect, width=1, border_radius=7
        )
        t_surf = font_sm.render(text, True, (255, 255, 255))
        screen.blit(
            t_surf,
            (
                rect.centerx - t_surf.get_width() // 2,
                rect.centery - t_surf.get_height() // 2,
            ),
        )

    draw_ui_button(
        top_buttons["mode"],
        f"Mode [F3]: {'Luyen Tap' if is_practice else 'Tu Do'}",
        (135, 55, 155) if is_practice else (45, 95, 145),
        is_practice,
    )
    draw_ui_button(
        top_buttons["song"],
        f"Bai [F4]: {state_info.get('song_title', 'Twinkle Star')}",
        (65, 80, 115),
    )
    draw_ui_button(
        top_buttons["restart"],
        "Reset [R]",
        (140, 55, 65),
    )
    draw_ui_button(
        top_buttons["input"],
        f"{state_info['input_mode_name']}",
        (40, 75, 115),
    )
    draw_ui_button(
        top_buttons["sustain"],
        f"Sustain: {'ON' if state_info['sustain_on'] else 'OFF'}",
        (40, 95, 75),
        state_info["sustain_on"],
    )

    # Cụm nút chỉnh Độ nhạy
    draw_ui_button(top_buttons["sens_down"], "-", (50, 60, 80))
    sens_lbl = font_sm.render(
        f"Nhay:{state_info['sens_pct']}%", True, (100, 255, 200)
    )
    screen.blit(
        sens_lbl,
        (
            (top_buttons["sens_down"].right + top_buttons["sens_up"].left - sens_lbl.get_width()) // 2,
            15,
        ),
    )
    draw_ui_button(top_buttons["sens_up"], "+", (50, 60, 80))

    # Cụm nút chỉnh Độ trong suốt
    draw_ui_button(top_buttons["opac_down"], "-", (50, 60, 80))
    opac_lbl = font_sm.render(
        f"Mo:{transparency_pct}%", True, (255, 220, 110)
    )
    screen.blit(
        opac_lbl,
        (
            (top_buttons["opac_down"].right + top_buttons["opac_up"].left - opac_lbl.get_width()) // 2,
            15,
        ),
    )
    draw_ui_button(top_buttons["opac_up"], "+", (50, 60, 80))

    # Cụm nút Chỉnh vị trí đàn
    edit_pos_on = state_info.get("edit_pos_mode", False)
    draw_ui_button(
        top_buttons["pos_mode"],
        "ViTri[F2]",
        (120, 85, 35),
        edit_pos_on,
    )
    draw_ui_button(top_buttons["pos_up"], "^", (50, 60, 80))
    draw_ui_button(top_buttons["pos_down"], "v", (50, 60, 80))

    # Hàng 2: Hiển thị Hợp âm bên phải & Thông tin chế độ chơi bên trái
    chord_box = pygame.Rect(925, 48, 340, 34)
    pygame.draw.rect(screen, (28, 36, 54), chord_box, border_radius=7)
    pygame.draw.rect(screen, (90, 220, 180), chord_box, width=1, border_radius=7)
    chord_surf = font_md.render(
        state_info["chord_text"], True, (100, 255, 210)
    )
    screen.blit(
        chord_surf,
        (
            chord_box.centerx - chord_surf.get_width() // 2,
            chord_box.centery - chord_surf.get_height() // 2,
        ),
    )

    if is_practice:
        info_line = (
            f"LUYEN TAP (CHO NOT)  |  "
            f"Diem: {state_info['score']}  |  "
            f"Combo: {state_info['combo']}x (Max: {state_info['max_combo']}x)  |  "
            f"Chinh xac: {state_info['accuracy']}%  |  "
            f"Trang thai: {state_info['last_judge']}"
        )
        info_col = (255, 235, 120)
    else:
        history_str = (
            " -> ".join(state_info["note_history"])
            if state_info["note_history"]
            else "Chua co not nao (Dat ngon tay vao phim va NHAN XUONG)"
        )
        info_line = (
            f"TU DO  |  Luc nhan: {state_info['last_vel_pct']}%  |  "
            f"Vi tri Y: {piano_top}px  |  "
            f"Nhat ky: {history_str}"
        )
        info_col = (190, 225, 255)

    info_surf = font_sm.render(info_line, True, info_col)
    screen.blit(info_surf, (15, 55))