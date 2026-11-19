"""Render the approved 30-second Ruiyinchang product promotion."""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from array import array
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FPS = 30
DURATION = 30
SAMPLE_RATE = 48_000

BG = "#090B0E"
PANEL = "#111419"
PANEL_ALT = "#171B20"
GOLD = "#C6A66A"
GOLD_DIM = "#756447"
WHITE = "#F4F1E8"
MUTED = "#AEB4BC"
GRID = "#242930"
RED = "#EC6B74"
GREEN = "#70D6B8"


@dataclass(frozen=True)
class Scene:
    start: float
    end: float
    title: str
    voiceover: str
    key: str


@dataclass(frozen=True)
class FormatSpec:
    name: str
    size: tuple[int, int]
    safe: tuple[int, int, int, int]

    @property
    def portrait(self) -> bool:
        return self.size[1] > self.size[0]


@dataclass(frozen=True)
class AudioCue:
    time: float
    kind: str


SCENES = (
    Scene(0, 3, "一场演出，不能只凭经验", "一场演出，不能只凭经验。", "hook"),
    Scene(3, 8, "证据进入同一视野", "锐音场 AI 决策风控中台，将艺人、城市、成本与风险证据汇入同一视野。", "evidence"),
    Scene(8, 14, "双口径保本 · 三情景测算", "双口径保本、三情景测算，让关键参数实时可见；", "finance"),
    Scene(14, 20, "缺项止步 · 风险前置", "评分、红线与人工核验，让缺项止步、风险前置。", "risk"),
    Scene(20, 26, "每一步都有依据", "从立项、报批，到招商、票务、执行与复盘，每一步都有依据。", "stages"),
    Scene(26, 30, "锐音场 AI 决策风控中台", "锐音场，让每一场演出，算得清、控得住、走得稳。", "brand"),
)

FORMATS = {
    "16x9": FormatSpec("16x9", (1920, 1080), (154, 86, 1766, 994)),
    "9x16": FormatSpec("9x16", (1080, 1920), (108, 230, 972, 1574)),
}

AUDIO_CUES = (
    AudioCue(0.05, "impact"),
    AudioCue(2.25, "scan"),
    AudioCue(3.15, "impact"),
    AudioCue(8.10, "scan"),
    AudioCue(14.10, "scan"),
    AudioCue(17.15, "lock"),
    *(AudioCue(20.35 + index * 0.82, "stage") for index in range(6)),
    AudioCue(26.20, "brand"),
)

FONT_CANDIDATES = (
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


def safe_rect(format_name: str) -> tuple[int, int, int, int]:
    return FORMATS[format_name].safe


def voiceover_text() -> str:
    return "".join(scene.voiceover for scene in SCENES)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease(value: float) -> float:
    value = clamp(value)
    return 1 - (1 - value) ** 3


def pulse(value: float) -> float:
    return 0.5 + 0.5 * math.sin(value * math.tau)


def scene_at(seconds: float) -> tuple[Scene, float]:
    seconds = clamp(seconds, 0, DURATION - 1 / FPS)
    for scene in SCENES:
        if scene.start <= seconds < scene.end:
            return scene, (seconds - scene.start) / (scene.end - scene.start)
    return SCENES[-1], 1.0


@lru_cache(maxsize=128)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size=size, index=1 if bold else 0)
            except OSError:
                try:
                    return ImageFont.truetype(candidate, size=size)
                except OSError:
                    pass
    return ImageFont.load_default()


def text_box(draw: ImageDraw.ImageDraw, text: str, face, anchor: str = "la") -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=face, anchor=anchor)
    return box[2] - box[0], box[3] - box[1]


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, minimum: int = 20):
    size = start
    while size > minimum:
        face = font(size, bold=True)
        if text_box(draw, text, face)[0] <= max_width:
            return face
        size -= 2
    return font(minimum, bold=True)


def rounded(draw, box, radius=16, fill=PANEL, outline=None, width=1):
    draw.rounded_rectangle(tuple(int(value) for value in box), radius=radius, fill=fill, outline=outline, width=width)


def draw_grid(draw: ImageDraw.ImageDraw, spec: FormatSpec):
    width, height = spec.size
    gap = 80 if not spec.portrait else 72
    for x in range(0, width, gap):
        draw.line((x, 0, x, height), fill=GRID, width=1)
    for y in range(0, height, gap):
        draw.line((0, y, width, y), fill=GRID, width=1)


def draw_chrome(draw: ImageDraw.ImageDraw, spec: FormatSpec, seconds: float):
    width, height = spec.size
    margin = 60 if not spec.portrait else 48
    draw.text((margin, margin), "锐音场", font=font(28, True), fill=WHITE)
    draw.text((margin + 105, margin + 3), "AI 决策风控中台", font=font(19), fill=GOLD)
    draw.text((width - margin, margin + 4), f"{seconds:04.1f} / 30.0", font=font(18), fill=MUTED, anchor="ra")
    line_y = height - margin
    draw.line((margin, line_y, width - margin, line_y), fill=GRID, width=2)
    draw.line((margin, line_y, margin + (width - margin * 2) * seconds / DURATION, line_y), fill=GOLD, width=3)


def reveal_text(draw, xy, text, face, fill, progress, anchor="la"):
    if not text:
        return
    count = max(1, round(len(text) * ease(progress)))
    draw.text(xy, text[:count], font=face, fill=fill, anchor=anchor)


def draw_hook(draw: ImageDraw.ImageDraw, spec: FormatSpec, progress: float):
    width, height = spec.size
    cx, cy = width // 2, height // 2
    words = ("成本", "档期", "上座率", "合规")
    positions = (
        (0.18, 0.34), (0.77, 0.31), (0.18, 0.67), (0.79, 0.70),
    )
    for index, (word, position) in enumerate(zip(words, positions)):
        local = clamp(progress * 2.7 - index * 0.15)
        x = int(width * position[0])
        y = int(height * position[1])
        color = RED if local > 0.72 else MUTED
        draw.text((x, y), word, font=font(28 if not spec.portrait else 32, True), fill=color, anchor="mm")
        if local > 0:
            radius = int(15 + local * 24)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=2)
    radius = int((70 if not spec.portrait else 95) + progress * (300 if not spec.portrait else 260))
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=GOLD_DIM, width=3)
    title_size = 64 if not spec.portrait else 72
    title = "一场演出\n不能只凭经验"
    draw.multiline_text((cx, cy), title, font=font(title_size, True), fill=WHITE, anchor="mm", align="center", spacing=16)
    scan_x = int(width * progress)
    draw.rectangle((scan_x - 2, int(height * .18), scan_x + 2, int(height * .82)), fill=GOLD)


def card(draw, box, label, value, accent=GOLD, note=None, progress=1.0):
    rounded(draw, box, 14, PANEL_ALT, GRID, 2)
    x1, y1, x2, y2 = box
    draw.rectangle((x1, y1, x1 + 5, y2), fill=accent)
    draw.text((x1 + 22, y1 + 18), label, font=font(18), fill=MUTED)
    reveal_text(draw, (x1 + 22, y1 + 55), value, font(30, True), WHITE, progress)
    if note:
        draw.text((x2 - 18, y2 - 16), note, font=font(14), fill=accent, anchor="rs")


def draw_evidence(draw: ImageDraw.ImageDraw, spec: FormatSpec, progress: float):
    width, height = spec.size
    items = (
        ("艺人证据", "热度趋势", GREEN),
        ("城市证据", "市场资料", GOLD),
        ("成本证据", "费用口径", GOLD),
        ("风险证据", "人工核验", RED),
    )
    if spec.portrait:
        card_w, card_h, gap = width - 216, 190, 24
        top = 380
        boxes = [(108, top + i * (card_h + gap), 108 + card_w, top + i * (card_h + gap) + card_h) for i in range(4)]
    else:
        card_w, card_h, gap = 340, 190, 24
        left = (width - (card_w * 4 + gap * 3)) // 2
        top = 370
        boxes = [(left + i * (card_w + gap), top, left + i * (card_w + gap) + card_w, top + card_h) for i in range(4)]
    draw.text((width // 2, 245 if not spec.portrait else 265), "证据进入同一视野", font=font(62 if not spec.portrait else 64, True), fill=WHITE, anchor="mm")
    for index, (box, item) in enumerate(zip(boxes, items)):
        local = clamp(progress * 2.2 - index * .18)
        if local <= 0:
            continue
        label, value, accent = item
        card(draw, box, label, value, accent, "来源待核验" if index == 3 else "已关联", local)
    hub_y = 730 if not spec.portrait else 1320
    draw.line((width * .2, hub_y, width * .8, hub_y), fill=GOLD_DIM, width=3)
    draw.ellipse((width // 2 - 12, hub_y - 12, width // 2 + 12, hub_y + 12), fill=GOLD)


def draw_slider(draw, x1, y, x2, ratio, label, value):
    draw.text((x1, y - 42), label, font=font(19), fill=MUTED)
    draw.text((x2, y - 42), value, font=font(22, True), fill=WHITE, anchor="ra")
    draw.line((x1, y, x2, y), fill=GRID, width=8)
    knob_x = int(x1 + (x2 - x1) * ratio)
    draw.line((x1, y, knob_x, y), fill=GOLD, width=8)
    draw.ellipse((knob_x - 13, y - 13, knob_x + 13, y + 13), fill=GOLD)


def draw_finance(draw: ImageDraw.ImageDraw, spec: FormatSpec, progress: float):
    width, height = spec.size
    ratio = .42 + .18 * ease(progress)
    people = int(6200 + 2220 * ratio)
    profit = int(-86 + 258 * ratio)
    title_y = 230 if not spec.portrait else 245
    draw.text((width // 2, title_y), "双口径保本 · 三情景测算", font=fit_font(draw, "双口径保本 · 三情景测算", width - 170, 60), fill=WHITE, anchor="mm")
    if spec.portrait:
        panel = (108, 365, 972, 1450)
        rounded(draw, panel, 18, PANEL, GRID, 2)
        draw.text((145, 410), "演示项目", font=font(18, True), fill=GOLD)
        draw_slider(draw, 145, 560, 935, ratio, "预计上座率", f"{int(ratio * 100)}%")
        card(draw, (145, 650, 935, 830), "现金保本人数", f"{people:,}", GREEN, "实时测算", progress)
        card(draw, (145, 860, 935, 1040), "全成本保本人数", f"{people + 1280:,}", GOLD, "实时测算", progress)
        card(draw, (145, 1070, 935, 1250), "基准情景利润", f"{profit:+d} 万", RED if profit < 0 else GREEN, "非收益承诺", progress)
    else:
        panel = (160, 330, 1760, 820)
        rounded(draw, panel, 18, PANEL, GRID, 2)
        draw.text((205, 375), "演示项目", font=font(18, True), fill=GOLD)
        draw_slider(draw, 205, 520, 860, ratio, "预计上座率", f"{int(ratio * 100)}%")
        card(draw, (970, 390, 1320, 610), "现金保本人数", f"{people:,}", GREEN, "实时测算", progress)
        card(draw, (1350, 390, 1710, 610), "全成本保本人数", f"{people + 1280:,}", GOLD, "实时测算", progress)
        card(draw, (970, 640, 1710, 790), "基准情景利润", f"{profit:+d} 万", RED if profit < 0 else GREEN, "非收益承诺", progress)


def draw_risk(draw: ImageDraw.ImageDraw, spec: FormatSpec, progress: float):
    width, height = spec.size
    title_y = 230 if not spec.portrait else 245
    draw.text((width // 2, title_y), "缺项止步 · 风险前置", font=font(60 if not spec.portrait else 66, True), fill=WHITE, anchor="mm")
    items = (
        ("档期授权证明", "已核验", GREEN),
        ("场馆档期确认", "待核验", GOLD),
        ("安全审批材料", "缺项", RED),
        ("票务参数来源", "已核验", GREEN),
    )
    left = 170 if not spec.portrait else 108
    right = width - left
    top = 350
    row_h = 112 if not spec.portrait else 190
    for index, (label, status, accent) in enumerate(items):
        local = clamp(progress * 2.1 - index * .14)
        if local <= 0:
            continue
        y1 = top + index * (row_h + 16)
        rounded(draw, (left, y1, right, y1 + row_h), 12, PANEL, GRID, 2)
        draw.text((left + 28, y1 + row_h // 2), label, font=font(25 if not spec.portrait else 28, True), fill=WHITE, anchor="lm")
        draw.text((right - 28, y1 + row_h // 2), status, font=font(20, True), fill=accent, anchor="rm")
    if progress > .56:
        y = 850 if not spec.portrait else 1320
        rounded(draw, (left, y, right, y + 100), 12, "#24151A", RED, 2)
        draw.text((width // 2, y + 50), "推进已拦截 · 请完成人工核验", font=font(26 if not spec.portrait else 30, True), fill=RED, anchor="mm")


def draw_stages(draw: ImageDraw.ImageDraw, spec: FormatSpec, progress: float):
    width, height = spec.size
    stages = ("立项", "报批", "招商", "票务", "执行", "复盘")
    draw.text((width // 2, 235 if not spec.portrait else 245), "六阶段有序推进", font=font(62 if not spec.portrait else 70, True), fill=WHITE, anchor="mm")
    active = min(5, int(progress * 6.5))
    if spec.portrait:
        x = 250
        top, gap = 390, 190
        draw.line((x, top, x, top + gap * 5), fill=GRID, width=8)
        for index, label in enumerate(stages):
            y = top + index * gap
            lit = index <= active
            draw.ellipse((x - 26, y - 26, x + 26, y + 26), fill=GREEN if index < active else GOLD if lit else PANEL_ALT, outline=GOLD if lit else GRID, width=4)
            draw.text((x + 70, y), label, font=font(34, True), fill=WHITE if lit else MUTED, anchor="lm")
            draw.text((x + 300, y), "已核验" if index < active else "当前阶段" if index == active else "待推进", font=font(21), fill=GREEN if index < active else GOLD if index == active else MUTED, anchor="lm")
    else:
        left, right, y = 200, width - 200, 560
        draw.line((left, y, right, y), fill=GRID, width=8)
        for index, label in enumerate(stages):
            x = int(left + (right - left) * index / 5)
            lit = index <= active
            draw.ellipse((x - 30, y - 30, x + 30, y + 30), fill=GREEN if index < active else GOLD if lit else PANEL_ALT, outline=GOLD if lit else GRID, width=4)
            draw.text((x, y + 78), label, font=font(27, True), fill=WHITE if lit else MUTED, anchor="mm")
            draw.text((x, y + 118), "已核验" if index < active else "当前阶段" if index == active else "待推进", font=font(16), fill=GREEN if index < active else GOLD if index == active else MUTED, anchor="mm")
    draw.text((width // 2, height - (190 if spec.portrait else 210)), "每一步都有依据", font=font(44 if not spec.portrait else 52, True), fill=GOLD, anchor="mm")


def draw_brand(draw: ImageDraw.ImageDraw, spec: FormatSpec, progress: float):
    width, height = spec.size
    cx, cy = width // 2, height // 2
    radius = int((80 + 130 * ease(progress)) * (1.25 if spec.portrait else 1))
    for ring in range(3):
        ring_radius = radius + ring * 34
        draw.arc((cx - ring_radius, cy - ring_radius, cx + ring_radius, cy + ring_radius), -120, -120 + int(300 * ease(progress)), fill=GOLD if ring == 0 else GOLD_DIM, width=5 - ring)
    draw.text((cx, cy - (155 if not spec.portrait else 230)), "锐音场", font=font(92 if not spec.portrait else 112, True), fill=WHITE, anchor="mm")
    draw.text((cx, cy - (65 if not spec.portrait else 115)), "AI 决策风控中台", font=font(36 if not spec.portrait else 44, True), fill=GOLD, anchor="mm")
    line = "让每一场演出"
    promise = "算得清 · 控得住 · 走得稳"
    draw.text((cx, cy + (105 if not spec.portrait else 170)), line, font=font(29 if not spec.portrait else 34), fill=MUTED, anchor="mm")
    reveal_text(draw, (cx, cy + (165 if not spec.portrait else 240)), promise, font(44 if not spec.portrait else 48, True), WHITE, clamp(progress * 1.6 - .25), "mm")


SCENE_DRAWERS = {
    "hook": draw_hook,
    "evidence": draw_evidence,
    "finance": draw_finance,
    "risk": draw_risk,
    "stages": draw_stages,
    "brand": draw_brand,
}


def draw_subtitle(draw: ImageDraw.ImageDraw, spec: FormatSpec, scene: Scene, progress: float):
    if scene.key in {"hook", "brand"}:
        return
    width, height = spec.size
    y = height - (155 if not spec.portrait else 270)
    face = fit_font(draw, scene.title, int(width * .8), 31 if not spec.portrait else 38)
    text_width, text_height = text_box(draw, scene.title, face, "mm")
    padding_x, padding_y = 24, 16
    rounded(draw, (width // 2 - text_width // 2 - padding_x, y - text_height // 2 - padding_y,
                   width // 2 + text_width // 2 + padding_x, y + text_height // 2 + padding_y), 8, "#111419", GRID, 1)
    reveal_text(draw, (width // 2, y), scene.title, face, WHITE, clamp(progress * 2.4), "mm")


def render_frame(format_name: str, seconds: float, size: tuple[int, int] | None = None) -> Image.Image:
    spec = FORMATS[format_name]
    target_size = size or spec.size
    target_spec = spec if target_size == spec.size else FormatSpec(spec.name, target_size, tuple(
        round(value * target_size[index % 2] / spec.size[index % 2])
        for index, value in enumerate(spec.safe)
    ))
    image = Image.new("RGB", target_spec.size, BG)
    draw = ImageDraw.Draw(image)
    draw_grid(draw, target_spec)
    scene, progress = scene_at(seconds)
    SCENE_DRAWERS[scene.key](draw, target_spec, progress)
    draw_subtitle(draw, target_spec, scene, progress)
    draw_chrome(draw, target_spec, seconds)
    return image


def media_contract(format_name: str, probe: dict) -> list[str]:
    expected = FORMATS[format_name]
    failures = []
    if abs(float(probe.get("duration", 0)) - DURATION) > .1:
        failures.append("duration")
    if (probe.get("width"), probe.get("height")) != expected.size:
        failures.append("size")
    if probe.get("frame_rate") != "30/1":
        failures.append("frame_rate")
    if probe.get("video_codec") != "h264":
        failures.append("video_codec")
    if probe.get("audio_codec") != "aac":
        failures.append("audio_codec")
    return failures


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, text=True, **kwargs)


def audio_duration(path: Path) -> float:
    result = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], capture_output=True)
    return float(result.stdout.strip())


def choose_mandarin_voice() -> str:
    result = run(["say", "-v", "?"], capture_output=True)
    for preferred in ("Tingting", "Reed (中文（中国大陆）)", "Eddy (中文（中国大陆）)"):
        if any(line.startswith(preferred) and "zh_CN" in line for line in result.stdout.splitlines()):
            return preferred
    raise RuntimeError("No Mandarin macOS voice is installed")


def generate_voiceover(work_dir: Path) -> Path:
    voice = choose_mandarin_voice()
    tracks = []
    filter_parts = []
    inputs = []
    for index, scene in enumerate(SCENES):
        target = scene.end - scene.start - .25
        rate = 215
        output = work_dir / f"voice-{index}.aiff"
        for _ in range(3):
            run(["say", "-v", voice, "-r", str(rate), "-o", str(output), scene.voiceover])
            duration = audio_duration(output)
            if duration <= target:
                break
            rate = min(360, math.ceil(rate * duration / target * 1.04))
        if audio_duration(output) > target + .08:
            raise RuntimeError(f"Voiceover scene {index + 1} does not fit its timeline")
        tracks.append(output)
        inputs.extend(["-i", str(output)])
        delay = round((scene.start + .08) * 1000)
        filter_parts.append(
            f"[{index}:a]aresample={SAMPLE_RATE},adelay={delay}|{delay},volume=1.15[v{index}]"
        )
    joined = "".join(f"[v{index}]" for index in range(len(tracks)))
    output = work_dir / "voiceover.wav"
    filter_complex = ";".join(filter_parts + [
        f"{joined}amix=inputs={len(tracks)}:normalize=0,atrim=0:{DURATION},apad=pad_dur={DURATION}[voice]",
    ])
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
        "-filter_complex", filter_complex, "-map", "[voice]",
        "-ar", str(SAMPLE_RATE), "-ac", "2", "-t", str(DURATION), str(output),
    ])
    return output


def _cue_sample(kind: str, elapsed: float) -> float:
    durations = {"impact": .42, "scan": .55, "lock": .38, "stage": .18, "brand": .9}
    duration = durations[kind]
    if elapsed < 0 or elapsed >= duration:
        return 0.0
    envelope = (1 - elapsed / duration) ** 2
    if kind == "impact":
        return envelope * (math.sin(math.tau * 72 * elapsed) + .35 * math.sin(math.tau * 145 * elapsed))
    if kind == "scan":
        frequency = 520 + 1100 * elapsed / duration
        return envelope * math.sin(math.tau * frequency * elapsed)
    if kind == "lock":
        return envelope * (1 if math.sin(math.tau * 185 * elapsed) >= 0 else -1)
    if kind == "stage":
        return envelope * math.sin(math.tau * 740 * elapsed)
    return envelope * (
        .65 * math.sin(math.tau * 220 * elapsed)
        + .45 * math.sin(math.tau * 330 * elapsed)
        + .3 * math.sin(math.tau * 440 * elapsed)
    )


def generate_music(path: Path, duration: float = DURATION, sample_rate: int = SAMPLE_RATE) -> Path:
    total = round(duration * sample_rate)
    samples = array("h")
    chord_sets = ((55, 82.41, 110), (61.74, 92.5, 123.47), (65.41, 98, 130.81))
    for index in range(total):
        seconds = index / sample_rate
        chord = chord_sets[min(2, int(seconds // 10))]
        beat_phase = seconds % .75
        kick = math.sin(math.tau * (72 - beat_phase * 45) * beat_phase) * math.exp(-beat_phase * 16)
        pulse_phase = seconds % .375
        tick = math.sin(math.tau * 910 * pulse_phase) * math.exp(-pulse_phase * 42)
        pad = sum(math.sin(math.tau * frequency * seconds + offset * .7)
                  for offset, frequency in enumerate(chord)) / len(chord)
        cue = sum(_cue_sample(item.kind, seconds - item.time) for item in AUDIO_CUES)
        fade = min(1, seconds / 1.3, (duration - seconds) / 1.2)
        base = fade * (.14 * pad + .19 * kick + .045 * tick + .24 * cue)
        shimmer = fade * .035 * math.sin(math.tau * (chord[-1] * 2) * seconds)
        left = int(clamp(base + shimmer, -1, 1) * 32767)
        right = int(clamp(base - shimmer, -1, 1) * 32767)
        samples.extend((left, right))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(samples.tobytes())
    return path


def mix_audio(work_dir: Path) -> Path:
    voice = generate_voiceover(work_dir)
    music = generate_music(work_dir / "music.wav")
    output = work_dir / "mix.wav"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(music), "-i", str(voice),
        "-filter_complex",
        (
            "[0:a]volume=0.58[music];"
            "[1:a]volume=1.0[voice];"
            "[music][voice]amix=inputs=2:duration=longest:normalize=0,"
            "loudnorm=I=-16:TP=-1:LRA=7,atrim=0:30,apad=pad_dur=30[mix]"
        ),
        "-map", "[mix]", "-ar", str(SAMPLE_RATE), "-ac", "2", "-t", str(DURATION), str(output),
    ])
    return output


def encode_video(format_name: str, mixed_audio: Path, output: Path) -> Path:
    spec = FORMATS[format_name]
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{spec.size[0]}x{spec.size[1]}",
        "-r", str(FPS), "-i", "pipe:0", "-i", str(mixed_audio),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", str(SAMPLE_RATE),
        "-t", str(DURATION), "-movflags", "+faststart", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        assert process.stdin is not None
        for frame_index in range(FPS * DURATION):
            frame = render_frame(format_name, frame_index / FPS)
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError(f"FFmpeg failed while encoding {format_name}")
    except BaseException:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.kill()
        process.wait()
        raise
    return output


def create_storyboard(path: Path) -> Path:
    thumb_size = (640, 360)
    gap = 18
    label_height = 54
    canvas = Image.new("RGB", (thumb_size[0] * 3 + gap * 4, (thumb_size[1] + label_height) * 2 + gap * 3), BG)
    draw = ImageDraw.Draw(canvas)
    for index, scene in enumerate(SCENES):
        frame = render_frame("16x9", (scene.start + scene.end) / 2)
        frame.thumbnail(thumb_size, Image.Resampling.LANCZOS)
        column, row = index % 3, index // 3
        x = gap + column * (thumb_size[0] + gap)
        y = gap + row * (thumb_size[1] + label_height + gap)
        canvas.paste(frame, (x, y))
        draw.text(
            (x, y + thumb_size[1] + 12),
            f"{scene.start:02.0f}–{scene.end:02.0f}s  {scene.title}",
            font=font(22, True), fill=WHITE,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, quality=92, subsampling=0)
    return path


def write_script(path: Path) -> Path:
    lines = [
        "锐音场 AI 决策风控中台｜30 秒产品宣传片",
        "",
        "说明：片中数值均为“演示项目”界面动效，不构成真实项目收益承诺。",
        "",
    ]
    for scene in SCENES:
        lines.extend([
            f"[{scene.start:05.1f}–{scene.end:05.1f}] {scene.title}",
            f"旁白：{scene.voiceover}",
            "",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def probe_media(path: Path) -> dict:
    result = run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate",
        "-of", "json", str(path),
    ], capture_output=True)
    data = json.loads(result.stdout)
    video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in data["streams"] if stream["codec_type"] == "audio")
    return {
        "duration": float(data["format"]["duration"]),
        "width": video["width"],
        "height": video["height"],
        "frame_rate": video["r_frame_rate"],
        "video_codec": video["codec_name"],
        "audio_codec": audio["codec_name"],
    }


def render_deliverables(output_dir: Path, work_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    mixed_audio = mix_audio(work_dir)
    outputs = {}
    for format_name in FORMATS:
        path = output_dir / f"ruiyinchang-product-promo-30s-{format_name}.mp4"
        encode_video(format_name, mixed_audio, path)
        probe = probe_media(path)
        failures = media_contract(format_name, probe)
        if failures:
            raise RuntimeError(f"{format_name} media contract failed: {', '.join(failures)}")
        outputs[format_name] = {"path": str(path), **probe}
    outputs["storyboard"] = str(create_storyboard(output_dir / "ruiyinchang-product-promo-30s-storyboard.jpg"))
    outputs["script"] = str(write_script(output_dir / "ruiyinchang-product-promo-30s-script.txt"))
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=FORMATS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audio-only", action="store_true")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--all", action="store_true")
    options = parser.parse_args(argv)
    if not options.audio_only and not options.all and (not options.format or not options.output):
        parser.error("use --all, --audio-only, or provide --format and --output")
    if options.work_dir:
        options.work_dir.mkdir(parents=True, exist_ok=True)
        context = None
        work_dir = options.work_dir
    else:
        context = tempfile.TemporaryDirectory(prefix="ruiyinchang-promo-")
        work_dir = Path(context.name)
    try:
        if options.audio_only:
            mixed = mix_audio(work_dir)
            print(json.dumps({"audio": str(mixed), "duration": audio_duration(mixed)}, ensure_ascii=False))
            return 0
        if options.all:
            output_dir = Path("deliverables")
            print(json.dumps(render_deliverables(output_dir, work_dir), ensure_ascii=False, indent=2))
            return 0
        mixed = mix_audio(work_dir)
        output = encode_video(options.format, mixed, options.output)
        probe = probe_media(output)
        failures = media_contract(options.format, probe)
        if failures:
            raise RuntimeError(f"Media contract failed: {', '.join(failures)}")
        print(json.dumps({"path": str(output), **probe}, ensure_ascii=False))
        return 0
    finally:
        if context:
            context.cleanup()


if __name__ == "__main__":
    sys.exit(main())
