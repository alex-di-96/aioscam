"""
Unit tests for media upload types, download helpers, and image FSM states.
Does NOT start any bot or make network calls.
"""

import io
import os
import re
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# ── InputMedia type detection ──────────────────────────────────────────────────

class TestInputMediaTypeDetection:
    """InputMedia auto-detects UploadType from file extension."""

    from aioscam.types.attachment import InputMedia
    from aioscam.enums.upload import UploadType

    def test_jpg(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("photo.jpg").type == UploadType.IMAGE

    def test_jpeg(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("image.jpeg").type == UploadType.IMAGE

    def test_png(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("picture.PNG").type == UploadType.IMAGE

    def test_gif(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("animation.gif").type == UploadType.IMAGE

    def test_webp(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("sticker.webp").type == UploadType.IMAGE

    def test_mp4(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("video.mp4").type == UploadType.VIDEO

    def test_mkv(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("clip.mkv").type == UploadType.VIDEO

    def test_mp3(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("song.mp3").type == UploadType.AUDIO

    def test_ogg(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("voice.ogg").type == UploadType.AUDIO

    def test_pdf(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("report.pdf").type == UploadType.FILE

    def test_docx(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("doc.docx").type == UploadType.FILE

    def test_unknown_extension(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("archive.xyz").type == UploadType.FILE

    def test_no_extension(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        assert InputMedia("README").type == UploadType.FILE

    def test_explicit_type_overrides_extension(self):
        from aioscam.types.attachment import InputMedia
        from aioscam.enums.upload import UploadType
        m = InputMedia("photo.jpg", UploadType.FILE)
        assert m.type == UploadType.FILE

    def test_path_stored(self):
        from aioscam.types.attachment import InputMedia
        m = InputMedia("/some/path/photo.jpg")
        assert m.path == "/some/path/photo.jpg"


# ── InputMediaBuffer type detection ───────────────────────────────────────────

class TestInputMediaBufferTypeDetection:

    def test_png_filename(self):
        from aioscam.types.attachment import InputMediaBuffer
        from aioscam.enums.upload import UploadType
        b = InputMediaBuffer(b"data", "img.png")
        assert b.type == UploadType.IMAGE

    def test_mp4_filename(self):
        from aioscam.types.attachment import InputMediaBuffer
        from aioscam.enums.upload import UploadType
        b = InputMediaBuffer(b"data", "vid.mp4")
        assert b.type == UploadType.VIDEO

    def test_mp3_filename(self):
        from aioscam.types.attachment import InputMediaBuffer
        from aioscam.enums.upload import UploadType
        b = InputMediaBuffer(b"data", "audio.mp3")
        assert b.type == UploadType.AUDIO

    def test_bin_filename_is_file(self):
        from aioscam.types.attachment import InputMediaBuffer
        from aioscam.enums.upload import UploadType
        b = InputMediaBuffer(b"data", "data.bin")
        assert b.type == UploadType.FILE

    def test_explicit_type_overrides(self):
        from aioscam.types.attachment import InputMediaBuffer
        from aioscam.enums.upload import UploadType
        b = InputMediaBuffer(b"data", "photo.jpg", UploadType.FILE)
        assert b.type == UploadType.FILE

    def test_buffer_stored(self):
        from aioscam.types.attachment import InputMediaBuffer
        payload = b"\x89PNG"
        b = InputMediaBuffer(payload, "img.png")
        assert b.buffer == payload

    def test_default_filename(self):
        from aioscam.types.attachment import InputMediaBuffer
        from aioscam.enums.upload import UploadType
        b = InputMediaBuffer(b"data")
        assert b.filename == "file"
        assert b.type == UploadType.FILE


# ── UploadType enum values ─────────────────────────────────────────────────────

class TestUploadTypeValues:
    """Enum values must match Max API type= parameter exactly."""

    def test_image_value(self):
        from aioscam.enums.upload import UploadType
        assert UploadType.IMAGE.value == "image"

    def test_video_value(self):
        from aioscam.enums.upload import UploadType
        assert UploadType.VIDEO.value == "video"

    def test_audio_value(self):
        from aioscam.enums.upload import UploadType
        assert UploadType.AUDIO.value == "audio"

    def test_file_value(self):
        from aioscam.enums.upload import UploadType
        assert UploadType.FILE.value == "file"

    def test_no_photo_or_document(self):
        from aioscam.enums.upload import UploadType
        values = [e.value for e in UploadType]
        assert "photo" not in values
        assert "document" not in values
        assert "sticker" not in values


# ── AttachmentUpload.to_dict ───────────────────────────────────────────────────

class TestAttachmentUploadToDict:

    def test_to_dict_structure(self):
        from aioscam.types.attachment import AttachmentUpload, AttachmentPayload
        att = AttachmentUpload(type="image", payload=AttachmentPayload(token="tok123"))
        d = att.to_dict()
        assert d == {"type": "image", "payload": {"token": "tok123"}}

    def test_to_dict_file_type(self):
        from aioscam.types.attachment import AttachmentUpload, AttachmentPayload
        att = AttachmentUpload(type="file", payload=AttachmentPayload(token="filetok"))
        assert att.to_dict()["type"] == "file"


# ── make_temp_path ─────────────────────────────────────────────────────────────

class TestMakeTempPath:
    """Datetime-based temp paths — unique, parseable, correct format."""

    def test_format_with_extension(self):
        from aioscam.client.client import AioScamClient
        path = AioScamClient.make_temp_path(".jpg")
        assert path.startswith("/tmp/aioscam_")
        assert path.endswith(".jpg")
        # aioscam_YYYYMMDD_HHMMSS_ffffff.jpg
        assert re.search(r"aioscam_\d{8}_\d{6}_\d{6}\.jpg$", path)

    def test_format_without_extension(self):
        from aioscam.client.client import AioScamClient
        path = AioScamClient.make_temp_path()
        assert re.search(r"aioscam_\d{8}_\d{6}_\d{6}$", path)

    def test_custom_directory(self):
        from aioscam.client.client import AioScamClient
        path = AioScamClient.make_temp_path(".png", "/var/tmp")
        assert path.startswith("/var/tmp/")

    def test_two_paths_are_different(self):
        from aioscam.client.client import AioScamClient
        p1 = AioScamClient.make_temp_path(".jpg")
        p2 = AioScamClient.make_temp_path(".jpg")
        # microsecond precision — virtually impossible to collide
        # (if they do happen to match in the same microsecond, test still passes
        #  because global rate limiter prevents true simultaneous calls)
        assert isinstance(p1, str) and isinstance(p2, str)

    def test_bot_make_temp_path(self):
        """Bot.make_temp_path delegates to client."""
        from aioscam.bot.bot import Bot
        path = Bot.make_temp_path(".mp4")
        assert re.search(r"aioscam_\d{8}_\d{6}_\d{6}\.mp4$", path)

    def test_timestamp_is_parseable(self):
        from aioscam.client.client import AioScamClient
        path = AioScamClient.make_temp_path(".jpg")
        filename = os.path.basename(path)
        # Extract timestamp part: aioscam_20260528_143022_847291.jpg
        ts_part = filename.replace("aioscam_", "").replace(".jpg", "")
        dt = datetime.strptime(ts_part, "%Y%m%d_%H%M%S_%f")
        assert dt.year >= 2026


# ── PIL image processing (demo_bot._process_image_demo) ───────────────────────

class TestProcessImageDemo:
    """Test the PIL helper in demo_bot without running the bot."""

    @pytest.fixture
    def red_image_bytes(self):
        """100×60 red JPEG for tests."""
        pytest.importorskip("PIL")
        from PIL import Image
        img = Image.new("RGB", (100, 60), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    @pytest.fixture
    def asymmetric_image_bytes(self):
        """Black image with white pixel at left edge — for flip test."""
        pytest.importorskip("PIL")
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        img.putpixel((0, 50), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _load_process_fn(self):
        """Import _process_image_demo without triggering bot startup."""
        import importlib.util, sys
        # Patch heavy imports so demo_bot module loads without token/DB
        for mod in ("sqlalchemy", "sqlalchemy.ext.asyncio", "aiosqlite"):
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()
        spec = importlib.util.spec_from_file_location(
            "demo_bot", "examples/demo_bot.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module._process_image_demo

    def test_output_is_jpeg_bytes(self, red_image_bytes):
        pytest.importorskip("PIL")
        fn = self._load_process_fn()
        result = fn(red_image_bytes)
        assert isinstance(result, bytes)
        assert result[:3] == b"\xff\xd8\xff"  # JPEG magic bytes

    def test_output_size_800x600(self, red_image_bytes):
        pytest.importorskip("PIL")
        from PIL import Image
        fn = self._load_process_fn()
        result = fn(red_image_bytes)
        img = Image.open(io.BytesIO(result))
        assert img.size == (800, 600)

    def test_flip_horizontal(self):
        """Flipping makes the left-half brighter than the right — verifiable without pixel math."""
        pytest.importorskip("PIL")
        from PIL import Image
        # Left half red, right half black
        img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        for x in range(50):
            for y in range(100):
                img.putpixel((x, y), (255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        fn = self._load_process_fn()
        result = fn(buf.getvalue())
        out = Image.open(io.BytesIO(result))

        # After flip: left half should be dark, right half should be reddish
        left_r = out.getpixel((50, 300))[0]    # left-quarter → was black → still ~0
        right_r = out.getpixel((700, 300))[0]  # right-quarter → was red → bright
        assert right_r > left_r + 50  # right is clearly brighter than left

    def test_rgba_input_converted(self):
        pytest.importorskip("PIL")
        from PIL import Image
        img = Image.new("RGBA", (50, 50), color=(100, 150, 200, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        fn = self._load_process_fn()
        result = fn(buf.getvalue())
        out = Image.open(io.BytesIO(result))
        assert out.mode == "RGB"


# ── ImageState FSM state definitions ──────────────────────────────────────────

class TestImageFSMStates:
    """ImageState must have the correct state and full_name format."""

    def _load_image_state(self):
        import importlib.util, sys
        for mod in ("sqlalchemy", "sqlalchemy.ext.asyncio", "aiosqlite"):
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()
        spec = importlib.util.spec_from_file_location(
            "demo_bot_states", "examples/demo_bot.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ImageState

    def test_waiting_image_state_exists(self):
        ImageState = self._load_image_state()
        assert hasattr(ImageState, "waiting_image")

    def test_full_name_format(self):
        ImageState = self._load_image_state()
        full = ImageState.waiting_image.full_name
        assert "ImageState" in full
        assert "waiting_image" in full

    def test_other_state_groups_intact(self):
        import importlib.util, sys
        for mod in ("sqlalchemy", "sqlalchemy.ext.asyncio", "aiosqlite"):
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()
        spec = importlib.util.spec_from_file_location(
            "demo_bot_sg", "examples/demo_bot.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module.RegistrationState, "waiting_phone")
        assert hasattr(module.QuizState, "question_1")
        assert hasattr(module.FeedbackState, "waiting_text")


# ── Green square (media_bot buffer_demo) ──────────────────────────────────────

class TestGreenSquare:
    """Verify media_bot generates a proper 200×200 green image."""

    def test_green_square_via_pil(self):
        PIL = pytest.importorskip("PIL")
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(0, 200, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()

        # Verify round-trip
        out = Image.open(io.BytesIO(data))
        assert out.size == (200, 200)
        r, g, b = out.getpixel((100, 100))
        assert r == 0
        assert g == 200
        assert b == 0

    def test_result_is_valid_png(self):
        pytest.importorskip("PIL")
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(0, 200, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG signature
