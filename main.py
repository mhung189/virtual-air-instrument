"""
Module: main.py
Phụ trách: Thành viên 5 (Nhóm trưởng / Tích hợp hệ thống)
Nhiệm vụ: Điều phối chế độ Chơi Tự Do (Free Play) trên 2 quãng tám (C3 -> B4).
"""

import os
import time
import numpy as np
import pygame

from audio_module import init_sound_bank, play_note, update_sustain_channels
from ui_module import (
    build_keyboard_layout,
    create_top_buttons,
    get_hovered_key,
    render_freeplay_scene,
)
from utils import detect_chord_name
from vision_module import HandTracker


def main():
    sounds = init_sound_bank()

    win_w, win_h = 1280, 720
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(
        "Virtual Webcam Piano - Free Play Studio (2 Octaves C3 -> B4)"
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

    (
        white_rects,
        black_rects,
        piano_top,
        _,
        pc_key_to_note,
        note_to_pc_label,
    ) = build_keyboard_layout(win_w, win_h)

    # Cấu hình chế độ Chơi Tự Do
    input_mode = 0  # 0: Webcam + Bàn phím | 1: Chỉ Bàn phím (60FPS) | 2: Chỉ Webcam
    input_mode_names = [
        "Webcam + Ban phim",
        "Chi Ban phim (60FPS)",
        "Chi Webcam",
    ]
    sustain_on = True
    key_glow_duration = 0.25

    key_active_until = {}
    active_channels = {}
    held_pc_keys = set()
    floating_particles = []
    note_history = []
    last_vel_pct = 0

    start_time = time.time()
    prev_frame_time = start_time

    def trigger_piano_key(note_str, volume):
        nonlocal last_vel_pct
        play_note(sounds, active_channels, note_str, volume)
        key_active_until[note_str] = time.time() + key_glow_duration
        last_vel_pct = int(round(volume * 100))

        note_history.append(note_str)
        if len(note_history) > 14:
            note_history.pop(0)

        rect = black_rects.get(note_str) or white_rects.get(note_str)
        if rect:
            p_col = (255, 185, 40) if "#" in note_str else (80, 255, 140)
            floating_particles.append(
                [rect.centerx, piano_top - 15, p_col, note_str]
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
                if top_buttons["input"].collidepoint(mx, my):
                    input_mode = (input_mode + 1) % 3
                elif top_buttons["sustain"].collidepoint(mx, my):
                    sustain_on = not sustain_on
                elif top_buttons["sens_down"].collidepoint(mx, my):
                    tracker.adjust_sensitivity(-1)
                elif top_buttons["sens_up"].collidepoint(mx, my):
                    tracker.adjust_sensitivity(1)
                elif top_buttons["clear"].collidepoint(mx, my):
                    note_history.clear()
                else:
                    clicked_note = get_hovered_key(
                        mx, my, black_rects, white_rects
                    )
                    if clicked_note:
                        trigger_piano_key(clicked_note, 0.90)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F1:
                    input_mode = (input_mode + 1) % 3
                elif event.key == pygame.K_SPACE:
                    sustain_on = not sustain_on
                elif event.key == pygame.K_LEFTBRACKET:
                    tracker.adjust_sensitivity(-1)
                elif event.key == pygame.K_RIGHTBRACKET:
                    tracker.adjust_sensitivity(1)

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

        # 2. Xử lý nhận diện thao tác "Nhấn để đánh" từ Webcam
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

        # 3. Quản lý ngân vang Sustain và nhận diện Hợp âm đang vang
        update_sustain_channels(
            active_channels, hovered_keys, key_active_until, now, sustain_on
        )
        currently_sounding = {
            k for k, exp_t in key_active_until.items() if exp_t > now
        } | held_pc_keys
        chord_text = detect_chord_name(currently_sounding)

        # 4. Kết xuất giao diện Chơi Tự Do
        state_info = {
            "input_mode_name": input_mode_names[input_mode],
            "sustain_on": sustain_on,
            "sens_pct": tracker.get_sensitivity_percent(),
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