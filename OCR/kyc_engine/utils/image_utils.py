from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps
from skimage.metrics import structural_similarity


def compare_signature_images(left: bytes, right: bytes) -> float:
    try:
        left_image = _prepare_signature(left)
        right_image = _prepare_signature(right)
        score = structural_similarity(left_image, right_image, data_range=255)
        return round(max(0.0, min(1.0, float(score))), 4)
    except Exception:
        return 0.0


def _prepare_signature(
    image_bytes: bytes, size: tuple[int, int] = (300, 100)
) -> np.ndarray:
    image = Image.open(BytesIO(image_bytes))
    grayscale = ImageOps.grayscale(image)
    array = np.array(grayscale, dtype=np.uint8)
    blurred = cv2.GaussianBlur(array, (5, 5), 0)
    threshold_value, thresholded = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    thresholded = cv2.threshold(
        blurred, min(int(threshold_value), 210), 255, cv2.THRESH_BINARY_INV
    )[1]
    resized = cv2.resize(thresholded, size, interpolation=cv2.INTER_AREA)
    return resized.astype(np.uint8)


def extract_signature_crop(image_bytes: bytes, prefer_bottom: bool) -> tuple[bytes, dict]:
    image = Image.open(BytesIO(image_bytes)).convert("L")
    array = np.array(image, dtype=np.uint8)
    height, width = array.shape[:2]

    if prefer_bottom:
        crop, meta = _extract_pan_signature(array, width, height)
    else:
        crop, meta = _extract_live_signature(array, width, height)

    output = Image.fromarray(crop)
    buffer = BytesIO()
    output.save(buffer, format="PNG")
    return buffer.getvalue(), meta


def _extract_pan_signature(
    array: np.ndarray, width: int, height: int
) -> tuple[np.ndarray, dict]:
    regions = [
        ("layout_primary", (0.30, 0.65, 0.75, 0.85), 0.0018),
        ("layout_secondary", (0.22, 0.60, 0.82, 0.90), 0.0012),
    ]

    for method, (x1r, y1r, x2r, y2r), ink_ratio in regions:
        x1 = int(width * x1r)
        y1 = int(height * y1r)
        x2 = int(width * x2r)
        y2 = int(height * y2r)
        region = array[y1:y2, x1:x2]
        mask, threshold = _signature_mask(region, threshold_cap=205)
        ink_pixels = int(cv2.countNonZero(mask))
        min_ink = max(140, int(region.shape[0] * region.shape[1] * ink_ratio))
        if ink_pixels < min_ink:
            continue

        bbox = _bbox_from_mask(mask, x1, y1, width, height, pad_x=14, pad_y=10)
        if bbox is None:
            continue

        bx1, by1, bx2, by2 = bbox
        crop = array[by1:by2, bx1:bx2]
        return crop, {
            "method": method,
            "bbox": [bx1, by1, bx2, by2],
            "orig_size": [width, height],
            "ink_pixels": ink_pixels,
            "ink_ok": True,
            "threshold": threshold,
        }

    x1 = int(width * 0.30)
    y1 = int(height * 0.65)
    x2 = int(width * 0.75)
    y2 = int(height * 0.85)
    return array[y1:y2, x1:x2], {
        "method": "layout_fallback",
        "bbox": [x1, y1, x2, y2],
        "orig_size": [width, height],
        "ink_pixels": 0,
        "ink_ok": False,
    }


def _extract_live_signature(
    array: np.ndarray, width: int, height: int
) -> tuple[np.ndarray, dict]:
    mask, threshold = _signature_mask(array, threshold_cap=220)
    ink_pixels = int(cv2.countNonZero(mask))
    min_ink = max(120, int(height * width * 0.0008))
    bbox = _bbox_from_mask(mask, 0, 0, width, height, pad_x=18, pad_y=14)
    if bbox is None or ink_pixels < min_ink:
        return array, {
            "method": "live_fallback",
            "bbox": [0, 0, width, height],
            "orig_size": [width, height],
            "ink_pixels": ink_pixels,
            "ink_ok": False,
            "threshold": threshold,
        }

    x1, y1, x2, y2 = bbox
    return array[y1:y2, x1:x2], {
        "method": "ink_bbox",
        "bbox": [x1, y1, x2, y2],
        "orig_size": [width, height],
        "ink_pixels": ink_pixels,
        "ink_ok": True,
        "threshold": threshold,
    }


def _signature_mask(region: np.ndarray, threshold_cap: int) -> tuple[np.ndarray, int]:
    blurred = cv2.GaussianBlur(region, (5, 5), 0)
    threshold_value, _ = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    threshold_value = min(int(threshold_value), threshold_cap)
    mask = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY_INV)[1]
    kernel = np.ones((2, 2), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask, threshold_value


def _bbox_from_mask(
    mask: np.ndarray,
    offset_x: int,
    offset_y: int,
    full_width: int,
    full_height: int,
    pad_x: int,
    pad_y: int,
) -> tuple[int, int, int, int] | None:
    coords = cv2.findNonZero(mask)
    if coords is None:
        return None

    x, y, w, h = cv2.boundingRect(coords)
    x1 = max(0, offset_x + x - pad_x)
    y1 = max(0, offset_y + y - pad_y)
    x2 = min(full_width, offset_x + x + w + pad_x)
    y2 = min(full_height, offset_y + y + h + pad_y)
    return x1, y1, x2, y2
