from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import fitz
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from PyPDF2 import PdfReader

from kyc_engine.models.schema import AuditEntry, KYCRequestFiles


@dataclass
class FilePayload:
    filename: str
    content_type: str
    data: bytes
    extension: str
    size_bytes: int


class FileValidator:
    MAX_DOC_SIZE = 5 * 1024 * 1024
    MAX_SIGNATURE_SIZE = 5 * 1024 * 1024
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    PDF_EXTENSIONS = {".pdf"}
    PDF_MIME_TYPES = {"application/pdf"}
    IMAGE_MIME_PREFIX = "image/"

    async def validate(
        self, files: KYCRequestFiles, audit_trail: list[AuditEntry]
    ) -> dict[str, FilePayload]:
        return {
            "pan_file": await self._validate_upload(
                files.pan_file,
                self.IMAGE_EXTENSIONS | self.PDF_EXTENSIONS,
                self.MAX_DOC_SIZE,
                "pan_file",
                audit_trail,
            ),
            "aadhaar_file": await self._validate_upload(
                files.aadhaar_file,
                self.IMAGE_EXTENSIONS | self.PDF_EXTENSIONS,
                self.MAX_DOC_SIZE,
                "aadhaar_file",
                audit_trail,
            ),
            "bank_statement": await self._validate_upload(
                files.bank_statement,
                self.PDF_EXTENSIONS,
                self.MAX_DOC_SIZE,
                "bank_statement",
                audit_trail,
            ),
            "live_signature": await self._validate_upload(
                files.live_signature,
                self.IMAGE_EXTENSIONS,
                self.MAX_SIGNATURE_SIZE,
                "live_signature",
                audit_trail,
            ),
        }

    async def _validate_upload(
        self,
        upload: UploadFile,
        allowed_extensions: set[str],
        max_size: int,
        label: str,
        audit_trail: list[AuditEntry],
    ) -> FilePayload:
        data = await upload.read()
        filename = upload.filename or label
        extension = Path(filename).suffix.lower()
        content_type = upload.content_type or "application/octet-stream"
        detected_type = self._detect_file_type(data, extension, content_type)

        if not self._is_allowed_type(detected_type, allowed_extensions):
            raise self._error(audit_trail, f"{label}: unsupported file type")
        if len(data) == 0:
            raise self._error(audit_trail, f"{label}: empty file")
        if len(data) > max_size:
            raise self._error(audit_trail, f"{label}: file size exceeds limit")

        self._check_corruption(extension, data, label, audit_trail)
        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="FILE_VALIDATION",
                message=f"{label}: validation passed",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return FilePayload(filename, content_type, data, extension, len(data))

    def _detect_file_type(self, data: bytes, extension: str, content_type: str) -> str:
        if data.startswith(b"%PDF"):
            return ".pdf"
        if extension in self.PDF_EXTENSIONS or content_type.lower() in self.PDF_MIME_TYPES:
            return ".pdf"

        try:
            image = Image.open(BytesIO(data))
            image_format = (image.format or "").lower()
            if image_format == "jpeg":
                return ".jpg"
            if image_format:
                return f".{image_format}"
        except (UnidentifiedImageError, OSError, ValueError):
            pass

        if extension in self.IMAGE_EXTENSIONS:
            return extension
        if content_type.lower().startswith(self.IMAGE_MIME_PREFIX):
            subtype = content_type.lower().split("/", 1)[1]
            if subtype == "jpeg":
                return ".jpg"
            return f".{subtype}"

        return extension

    @staticmethod
    def _is_allowed_type(detected_type: str, allowed_extensions: set[str]) -> bool:
        if detected_type == ".jpg":
            return ".jpg" in allowed_extensions or ".jpeg" in allowed_extensions
        if detected_type == ".jpeg":
            return ".jpg" in allowed_extensions or ".jpeg" in allowed_extensions
        return detected_type in allowed_extensions

    def _check_corruption(
        self,
        extension: str,
        data: bytes,
        label: str,
        audit_trail: list[AuditEntry],
    ) -> None:
        try:
            if extension in self.PDF_EXTENSIONS:
                reader = PdfReader(BytesIO(data))
                if reader.is_encrypted:
                    raise self._password_protected_error(audit_trail, label)
                fitz.open(stream=data, filetype="pdf").close()
            else:
                image = Image.open(BytesIO(data))
                image.verify()
        except HTTPException:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Exception) as exc:
            raise self._error(audit_trail, f"{label}: corruption check failed ({exc})") from exc

    def _password_protected_error(
        self,
        audit_trail: list[AuditEntry],
        label: str,
    ) -> HTTPException:
        audit_trail.append(
            AuditEntry(
                level="ERROR",
                stage="FILE_VALIDATION",
                message=f"{label}: File is password protected",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return HTTPException(
            status_code=400,
            detail={
                "error": "File is password protected",
                "audit_trail": [entry.model_dump() for entry in audit_trail],
            },
        )

    def _error(self, audit_trail: list[AuditEntry], message: str) -> HTTPException:
        audit_trail.append(
            AuditEntry(
                level="ERROR",
                stage="FILE_VALIDATION",
                message=message,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return HTTPException(
            status_code=400,
            detail={"error": message, "audit_trail": [entry.model_dump() for entry in audit_trail]},
        )
