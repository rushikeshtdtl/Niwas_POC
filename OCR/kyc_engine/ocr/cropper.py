import base64
from io import BytesIO

import fitz
from fastapi import HTTPException
from PIL import Image, ImageFilter, ImageOps
from PyPDF2 import PdfReader

from kyc_engine.core.file_validator import FilePayload


class DocumentCropper:
    @staticmethod
    def render_pdf_to_png(data: bytes, page_index: int = 0) -> bytes:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise HTTPException(status_code=400, detail="File is password protected")
        document = fitz.open(stream=data, filetype="pdf")
        safe_index = min(max(page_index, 0), len(document) - 1)
        page = document.load_page(safe_index)
        pixmap = page.get_pixmap(dpi=200)
        image = Image.open(BytesIO(pixmap.tobytes("png")))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        document.close()
        return buffer.getvalue()

    def open_document_image(
        self,
        file_payload: FilePayload,
        page_index: int = 0,
    ) -> Image.Image:
        if file_payload.extension == ".pdf":
            image = Image.open(
                BytesIO(self.render_pdf_to_png(file_payload.data, page_index=page_index))
            )
        else:
            image = Image.open(BytesIO(file_payload.data))
        image = ImageOps.exif_transpose(image)
        return image.convert("RGB")

    @staticmethod
    def normalize_image_for_ocr(
        image: Image.Image,
        document_type: str,
    ) -> Image.Image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        max_side = max(width, height)
        if max_side > 1800:
            scale = 1800 / max_side
            rgb = rgb.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )

        grayscale = ImageOps.grayscale(rgb)
        grayscale = ImageOps.autocontrast(grayscale)
        if document_type in {"pan", "aadhaar"}:
            grayscale = grayscale.filter(ImageFilter.SHARPEN)
        else:
            grayscale = grayscale.filter(ImageFilter.MedianFilter(size=3))

        return grayscale.convert("RGB")

    def render_statement_customer_crops(self, data: bytes) -> dict[str, bytes]:
        rendered: dict[str, bytes] = {}
        document = fitz.open(stream=data, filetype="pdf")
        page_count = min(2, len(document))
        document.close()
        for page_index in range(page_count):
            full_image = self.normalize_image_for_ocr(
                self.open_document_image(
                    FilePayload(
                        filename="statement.pdf",
                        content_type="application/pdf",
                        data=data,
                        extension=".pdf",
                        size_bytes=len(data),
                    ),
                    page_index=page_index,
                ),
                "statement",
            )
            width, height = full_image.size
            crops = {
                f"page-{page_index + 1}-customer-focus-top-left": (0, 0, int(width * 0.62), int(height * 0.45)),
                f"page-{page_index + 1}-customer-focus-top-band": (0, 0, width, int(height * 0.32)),
                f"page-{page_index + 1}-customer-focus-lower-left": (
                    0,
                    int(height * 0.28),
                    int(width * 0.72),
                    int(height * 0.78),
                ),
            }
            for name, box in crops.items():
                crop = full_image.crop(box)
                buffer = BytesIO()
                crop.save(buffer, format="PNG")
                rendered[name] = buffer.getvalue()
        return rendered

    def render_pan_focus_crops(self, file_payload: FilePayload) -> dict[str, bytes]:
        image = self.normalize_image_for_ocr(
            self.open_document_image(file_payload),
            "pan",
        )
        width, height = image.size
        crops = {
            "pan-core-center": (
                int(width * 0.08),
                int(height * 0.18),
                int(width * 0.92),
                int(height * 0.72),
            ),
            "pan-lower-details": (
                int(width * 0.10),
                int(height * 0.32),
                int(width * 0.90),
                int(height * 0.82),
            ),
            "pan-full-upper": (0, 0, width, int(height * 0.70)),
        }
        rendered: dict[str, bytes] = {}
        for name, box in crops.items():
            crop = image.crop(box)
            buffer = BytesIO()
            crop.save(buffer, format="PNG")
            rendered[name] = buffer.getvalue()
        return rendered

    def render_aadhaar_focus_crops(self, file_payload: FilePayload) -> dict[str, bytes]:
        image = self.normalize_image_for_ocr(
            self.open_document_image(file_payload),
            "aadhaar",
        )
        width, height = image.size
        crops = {
            "name-top-half": (0, 0, width, int(height * 0.55)),
            "name-upper-center": (int(width * 0.08), int(height * 0.10), int(width * 0.92), int(height * 0.52)),
            "address-bottom-half": (0, int(height * 0.45), width, height),
            "address-bottom-right": (int(width * 0.28), int(height * 0.32), width, height),
            "address-lower-left": (0, int(height * 0.30), int(width * 0.72), height),
            "address-full": (0, 0, width, height),
        }
        rendered: dict[str, bytes] = {}
        for name, box in crops.items():
            crop = image.crop(box)
            buffer = BytesIO()
            crop.save(buffer, format="PNG")
            rendered[name] = buffer.getvalue()
        return rendered

    def to_image_data_uri(
        self,
        file_payload: FilePayload,
        document_type: str,
        page_index: int = 0,
    ) -> str | None:
        try:
            image = self.open_document_image(file_payload, page_index=page_index)
            normalized = self.normalize_image_for_ocr(image, document_type)
            buffer = BytesIO()
            normalized.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
        except Exception:
            return None
        return self.image_bytes_to_data_uri(image_bytes)

    @staticmethod
    def image_bytes_to_data_uri(image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
