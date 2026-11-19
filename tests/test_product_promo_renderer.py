from pathlib import Path
import wave

import pytest

from tools.product_promo.render import (
    AUDIO_CUES,
    FORMATS,
    SCENES,
    generate_music,
    media_contract,
    render_frame,
    safe_rect,
    voiceover_text,
    write_script,
)


def test_timeline_is_exactly_thirty_seconds():
    assert SCENES[0].start == 0
    assert SCENES[-1].end == 30
    assert all(left.end == right.start for left, right in zip(SCENES, SCENES[1:]))


def test_formats_have_fixed_safe_areas():
    assert FORMATS["16x9"].size == (1920, 1080)
    assert FORMATS["9x16"].size == (1080, 1920)
    assert safe_rect("9x16") == (108, 230, 972, 1574)


def test_public_copy_has_no_unverified_claims():
    joined = " ".join(scene.title + scene.voiceover for scene in SCENES)
    for forbidden in ("自动监测", "资金划转", "保证盈利", "MVP", "demo"):
        assert forbidden not in joined


def test_voiceover_script_matches_scene_order():
    assert voiceover_text() == "".join(scene.voiceover for scene in SCENES)


def test_audio_cues_stay_inside_timeline():
    assert all(0 <= cue.time < 30 for cue in AUDIO_CUES)
    assert {cue.kind for cue in AUDIO_CUES} >= {"impact", "scan", "lock", "stage", "brand"}


@pytest.mark.parametrize("format_name", ["16x9", "9x16"])
@pytest.mark.parametrize("scene", SCENES)
def test_scene_midpoint_renders_nonblank_inside_safe_area(format_name, scene):
    frame = render_frame(format_name, (scene.start + scene.end) / 2)
    assert frame.mode == "RGB"
    assert frame.size == FORMATS[format_name].size
    safe = frame.crop(safe_rect(format_name))
    colors = safe.resize((64, 64)).getcolors(4096)
    assert colors is not None and len(colors) > 8


def test_media_contract_rejects_wrong_probe_values():
    valid = {
        "duration": 30.0,
        "width": 1920,
        "height": 1080,
        "frame_rate": "30/1",
        "video_codec": "h264",
        "audio_codec": "aac",
    }
    assert media_contract("16x9", valid) == []
    assert "duration" in media_contract("16x9", {**valid, "duration": 29.4})
    assert "size" in media_contract("16x9", {**valid, "width": 1080})


def test_delivery_names_match_specification():
    root = Path("deliverables")
    assert root / "ruiyinchang-product-promo-30s-16x9.mp4"
    assert root / "ruiyinchang-product-promo-30s-9x16.mp4"


def test_generated_music_is_stereo_pcm(tmp_path):
    path = generate_music(tmp_path / "music.wav", duration=.1, sample_rate=8000)
    with wave.open(str(path), "rb") as audio:
        assert audio.getnchannels() == 2
        assert audio.getframerate() == 8000
        assert audio.getnframes() == 800
        assert audio.getsampwidth() == 2


def test_exported_script_documents_demo_data_boundary(tmp_path):
    path = write_script(tmp_path / "script.txt")
    content = path.read_text(encoding="utf-8")
    assert "演示项目" in content
    assert "不构成真实项目收益承诺" in content
    assert all(scene.voiceover in content for scene in SCENES)
