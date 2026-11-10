"""
Module: audio_module.py
Phụ trách: Thành viên 2
Nhiệm vụ: Tổng hợp âm thanh 24 nốt (C3 -> B4), điều khiển lực gõ và chế độ ngân Sustain.
"""

import numpy as np
import pygame
from utils import END_MIDI, NOTE_NAMES, START_MIDI


def midi_to_freq(midi_num):
    """Chuyển đổi mã MIDI sang tần số chuẩn quốc tế (A4 = 440Hz)."""
    return 440.0 * (2.0 ** ((midi_num - 69) / 12.0))


def generate_piano_note(freq, duration=2.4, sample_rate=44100):
    """Tổng hợp âm thanh Grand Piano bằng 6 tầng sóng hài và đường bao ADSR."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = (
        1.00 * np.sin(2 * np.pi * freq * t)
        + 0.55 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-1.5 * t)
        + 0.30 * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-2.5 * t)
        + 0.15 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-3.5 * t)
        + 0.08 * np.sin(2 * np.pi * freq * 5 * t) * np.exp(-4.5 * t)
        + 0.04 * np.sin(2 * np.pi * freq * 6 * t) * np.exp(-5.5 * t)
    )

    attack_samples = int(0.008 * sample_rate)
    envelope = np.exp(-2.2 * t)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    wave = wave * envelope

    wave = wave / np.max(np.abs(wave))
    audio_data = (wave * 32767 * 0.78).astype(np.int16)
    stereo_data = np.column_stack((audio_data, audio_data))
    return pygame.sndarray.make_sound(stereo_data)


def init_sound_bank():
    """Khởi tạo Pygame Mixer 32 kênh và tạo mẫu âm thanh cho 24 phím (C3 -> B4)."""
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.init()
    pygame.mixer.set_num_channels(32)

    print("Đang khởi tạo bộ âm thanh 2 quãng tám chuẩn (C3 -> B4)...")
    sounds = {}
    for midi_code in range(START_MIDI, END_MIDI + 1):
        n_str = f"{NOTE_NAMES[midi_code % 12]}{(midi_code // 12) - 1}"
        sounds[n_str] = generate_piano_note(midi_to_freq(midi_code))
    return sounds


def play_note(sounds, active_channels, note_name, velocity_norm=0.85):
    """Phát nốt nhạc với âm lượng theo lực nhấn và lưu kênh phát."""
    if note_name in sounds:
        ch = sounds[note_name].play()
        if ch is not None:
            vol = float(np.clip(velocity_norm, 0.35, 1.0))
            ch.set_volume(vol)
            active_channels[note_name] = ch


def update_sustain_channels(
    active_channels, hovered_keys, key_active_until, now, sustain_on
):
    """Ngắt âm mượt mà (fadeout) khi nhả ngón tay nếu tắt Sustain Pedal."""
    if not sustain_on:
        for k_name in list(active_channels.keys()):
            if (
                k_name not in hovered_keys
                and key_active_until.get(k_name, 0) <= now
            ):
                active_channels[k_name].fadeout(240)
                del active_channels[k_name]