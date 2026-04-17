from datetime import datetime, timezone
from io import BytesIO

import fitz
from PIL import Image

from kyc_engine.core.file_validator import FilePayload
from kyc_engine.models.schema import AuditEntry
from kyc_engine.utils.image_utils import compare_signature_images, extract_signature_crop


class SignatureComparator:
    def compare(
        self,
        pan_file: FilePayload,
        live_signature: FilePayload,
        audit_trail: list[AuditEntry],
    ) -> float:
        pan_signature_source = pan_file.data
        if pan_file.extension == ".pdf":
            pan_signature_source = self._render_pdf_to_png(pan_file.data)

        pan_crop, pan_meta = extract_signature_crop(
            pan_signature_source, prefer_bottom=True
        )
        live_crop, live_meta = extract_signature_crop(
            live_signature.data, prefer_bottom=False
        )
        if not pan_meta.get("ink_ok"):
            raise ValueError("PAN signature not detected properly")
        if not live_meta.get("ink_ok"):
            raise ValueError("Live signature not detected properly")

        score = compare_signature_images(pan_crop, live_crop)
        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="SIGNATURE",
                message=(
                    f"Signature similarity score = {score}; "
                    f"pan_crop={pan_meta.get('bbox')} method={pan_meta.get('method')}; "
                    f"live_crop={live_meta.get('bbox')} method={live_meta.get('method')}"
                ),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return score

    @staticmethod
    def _render_pdf_to_png(data: bytes) -> bytes:
        document = fitz.open(stream=data, filetype="pdf")
        page = document.load_page(0)
        pixmap = page.get_pixmap(dpi=200)
        image = Image.open(BytesIO(pixmap.tobytes("png")))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        document.close()
        return buffer.getvalue()
