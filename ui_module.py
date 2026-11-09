"""
Module: ui_module.py
Phụ trách: Thành viên 4
Nhiệm vụ: Thiết kế giao diện Chơi Tự Do (Free Play), hiệu ứng lún phím 3D và bảng hiển thị hợp âm.
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


def build_keyboard_layout(width, height):
    """Tạo tọa độ cho 2 quãng tám (C3 -> B4: 14 phím trắng, 10 phím đen) ở cạnh dưới."""
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
    piano_bottom = height - 12
    white_h = 235
    piano_top = piano_bottom - white_h
    white_w = (width - 2 * margin_x) // len(white_notes)
    black_w = int(white_w * 0.60)
    black_h = int(white_h * 0.60)

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
    """Tạo các nút điều khiển dành riêng cho chế độ Chơi Tự Do."""
    return {
        "input": pygame.Rect(20, 12, 245, 38),
        "sustain": pygame.Rect(280, 12, 205, 38),
        "sens_down": pygame.Rect(500, 12, 40, 38),
        "sens_up": pygame.Rect(675, 12, 40, 38),
        "clear": pygame.Rect(1085, 12, 175, 38),
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
    note_to_pc_label,
    key_active_until,
    hovered_keys,
    floating_particles,
    hand_skeleton_pts,
    visual_tips,
    top_buttons,
    state_info,
):
    """Vẽ giao diện đàn Piano Chơi Tự Do, hiệu ứng hạt âm thanh và thanh thông tin."""
    font_sm, font_md, font_lg = fonts

    # 1. Vẽ hiệu ứng bong bóng tên nốt nhạc bay lên khi nhấn phím
    new_particles = []
    for p_x, p_y, p_col, p_lbl in floating_particles:
        if p_y > 95:
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
            new_particles.append([p_x, p_y - 5, p_col, p_lbl])
    floating_particles[:] = new_particles

    # Gờ nẹp đàn Piano phía trên bàn phím
    pygame.draw.rect(
        screen, (165, 35, 65), (30, piano_top - 10, win_w - 60, 10), border_radius=3
    )

    # 2. Vẽ 24 phím đàn (14 trắng, 10 đen) với hiệu ứng nhấn lún vật lý
    for name, rect in white_rects.items():
        is_active = key_active_until.get(name, 0) > now
        sink_px = 7 if is_active else 0

        if is_active:
            color = (95, 255, 135)
        elif name in hovered_keys:
            color = (205, 238, 255)
        else:
            color = (246, 246, 250)

        drawn_rect = pygame.Rect(
            rect.left, rect.top + sink_px, rect.width, rect.height - sink_px
        )
        pygame.draw.rect(
            screen,
            color,
            drawn_rect,
            border_bottom_left_radius=6,
            border_bottom_right_radius=6,
        )
        if not is_active:
            pygame.draw.rect(
                screen,
                (175, 180, 190),
                (rect.left, rect.bottom - 12, rect.width, 12),
                border_bottom_left_radius=6,
                border_bottom_right_radius=6,
            )
        pygame.draw.rect(
            screen,
            (40, 45, 55),
            drawn_rect,
            width=2,
            border_bottom_left_radius=6,
            border_bottom_right_radius=6,
        )

        pc_char = note_to_pc_label.get(name, "")
        if pc_char:
            key_badge = pygame.Rect(
                rect.centerx - 15, drawn_rect.bottom - 66, 30, 24
            )
            pygame.draw.rect(
                screen, (45, 55, 75), key_badge, border_radius=5
            )
            k_surf = font_sm.render(pc_char, True, (255, 230, 100))
            screen.blit(
                k_surf,
                (
                    key_badge.centerx - k_surf.get_width() // 2,
                    key_badge.centery - k_surf.get_height() // 2,
                ),
            )

        n_col = (200, 30, 30) if name.startswith("C") else (45, 45, 55)
        n_surf = font_md.render(name, True, n_col)
        screen.blit(
            n_surf,
            (
                rect.centerx - n_surf.get_width() // 2,
                drawn_rect.bottom - 36,
            ),
        )

    for name, rect in black_rects.items():
        is_active = key_active_until.get(name, 0) > now
        sink_px = 5 if is_active else 0

        if is_active:
            color = (255, 175, 30)
        elif name in hovered_keys:
            color = (75, 85, 105)
        else:
            color = (28, 30, 38)

        drawn_rect = pygame.Rect(
            rect.left, rect.top + sink_px, rect.width, rect.height - sink_px
        )
        pygame.draw.rect(
            screen,
            color,
            drawn_rect,
            border_bottom_left_radius=5,
            border_bottom_right_radius=5,
        )
        pygame.draw.rect(
            screen,
            (10, 10, 15),
            drawn_rect,
            width=2,
            border_bottom_left_radius=5,
            border_bottom_right_radius=5,
        )

        pc_char = note_to_pc_label.get(name, "")
        if pc_char:
            k_surf = font_sm.render(f"[{pc_char}]", True, (255, 220, 90))
            screen.blit(
                k_surf,
                (
                    rect.centerx - k_surf.get_width() // 2,
                    drawn_rect.bottom - 44,
                ),
            )

        n_surf = font_sm.render(name, True, (220, 225, 235))
        screen.blit(
            n_surf,
            (
                rect.centerx - n_surf.get_width() // 2,
                drawn_rect.bottom - 24,
            ),
        )

    # 3. Vẽ khung xương bàn tay và vòng đo lực nhấn trên từng đầu ngón tay
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

    # 4. Vẽ Thanh Studio HUD ở cạnh trên
    pygame.draw.rect(screen, (15, 20, 32), (0, 0, win_w, 86))
    pygame.draw.line(screen, (65, 80, 110), (0, 86), (win_w, 86), 2)

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
        top_buttons["input"],
        f"Dau vao: {state_info['input_mode_name']}",
        (40, 75, 115),
    )
    draw_ui_button(
        top_buttons["sustain"],
        f"Sustain [SPACE]: {'ON' if state_info['sustain_on'] else 'OFF'}",
        (40, 95, 75),
        state_info["sustain_on"],
    )

    draw_ui_button(top_buttons["sens_down"], "-", (50, 60, 80))
    sens_lbl = font_sm.render(
        f"Do nhay Nhan: {state_info['sens_pct']}%", True, (100, 255, 200)
    )
    screen.blit(sens_lbl, (548, 21))
    draw_ui_button(top_buttons["sens_up"], "+", (50, 60, 80))

    # Hiển thị Hợp âm / Nốt đang vang lên ở góc phải thanh công cụ
    chord_box = pygame.Rect(730, 12, 340, 38)
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

    draw_ui_button(
        top_buttons["clear"], "Xoa Lich Su [C]", (140, 50, 70)
    )

    # Dòng dưới: Lực nhấn gần nhất và chuỗi lịch sử các nốt vừa chơi
    history_str = (
        " -> ".join(state_info["note_history"])
        if state_info["note_history"]
        else "Chua co not nao (Hay dat ngon tay vao phim va NHAN XUONG)"
    )
    info_line = (
        f"Luc nhan: {state_info['last_vel_pct']}%   |   "
        f"Nhat ky not vua danh: {history_str}"
    )
    info_surf = font_sm.render(info_line, True, (190, 225, 255))
    screen.blit(info_surf, (20, 58))