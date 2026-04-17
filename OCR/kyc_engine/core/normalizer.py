from datetime import datetime, timezone

from kyc_engine.models.schema import AuditEntry, OCRBundle
from kyc_engine.utils.address_utils import normalize_address
from kyc_engine.utils.regex_utils import normalize_date


class Normalizer:
    def normalize(self, ocr_data: OCRBundle, audit_trail: list[AuditEntry]) -> dict:
        normalized = ocr_data.model_dump()

        for _, section in normalized.items():
            if not isinstance(section, dict):
                continue
            for key, value in section.items():
                text = str(value or "").strip()
                if key.endswith("_name") or key == "statement_name":
                    section[key] = " ".join(text.upper().split())
                elif key.endswith("_dob"):
                    section[key] = normalize_date(text)
                elif key.endswith("_address"):
                    section[key] = normalize_address(text)
                elif key == "aadhaar_number":
                    section[key] = "".join(ch for ch in text if ch.isdigit())
                else:
                    section[key] = text

        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="NORMALIZATION",
                message="Structured OCR data normalized",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return normalized
