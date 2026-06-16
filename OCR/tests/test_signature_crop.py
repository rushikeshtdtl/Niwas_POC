from io import BytesIO

from PIL import Image, ImageDraw

from kyc_engine.utils.image_utils import extract_signature_crop


def _to_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_signature_crop_prefers_bottom_region() -> None:
    width, height = 900, 600
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Simulated header text/noise.
    for y in range(30, 160, 20):
        draw.text((40, y), "ACCOUNT STATEMENT HEADER", fill="black")

    # Simulated signature scribble at bottom-right.
    points = [
        (560, 470),
        (610, 455),
        (655, 485),
        (705, 460),
        (770, 490),
        (830, 465),
    ]
    draw.line(points, fill="black", width=6, joint="curve")
    draw.line([(590, 510), (690, 520), (820, 505)], fill="black", width=5)

    cropped_bytes, meta = extract_signature_crop(_to_bytes(image), prefer_bottom=True)
    x1, y1, x2, y2 = meta["bbox"]

    assert meta["method"] == "layout_primary"
    assert meta["ink_ok"] is True
    assert y1 >= int(height * 0.60)
    assert y2 > int(height * 0.70)
    assert x1 >= int(width * 0.25)
    assert x2 > int(width * 0.70)
    assert (x2 - x1) < width
    assert (y2 - y1) < height

    cropped = Image.open(BytesIO(cropped_bytes))
    assert cropped.size[0] < width
    assert cropped.size[1] < height


def test_signature_crop_live_signature_uses_full_frame() -> None:
    width, height = 500, 250
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.line([(40, 120), (140, 70), (260, 150), (430, 90)], fill="black", width=6)

    cropped_bytes, meta = extract_signature_crop(_to_bytes(image), prefer_bottom=False)
    x1, y1, x2, y2 = meta["bbox"]

    assert meta["ink_ok"] is True
    # Should crop around ink, not fallback to bottom-right.
    assert x1 < int(width * 0.4)
    assert y1 < int(height * 0.6)
    assert x2 > int(width * 0.6)


def test_pan_signature_crop_marks_missing_ink() -> None:
    width, height = 900, 600
    image = Image.new("RGB", (width, height), "white")

    _, meta = extract_signature_crop(_to_bytes(image), prefer_bottom=True)

    assert meta["method"] == "layout_fallback"
    assert meta["ink_ok"] is False
