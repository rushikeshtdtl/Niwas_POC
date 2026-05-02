import re
import time
from datetime import datetime, timezone
from io import BytesIO

import cv2
import numpy as np
import requests
from fastapi import HTTPException
from PIL import Image

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

from kyc_engine.config import get_settings
from kyc_engine.core.file_validator import FilePayload
from kyc_engine.models.schema import AuditEntry, OCRBundle, OCRLog
from kyc_engine.ocr.parser import OCRParser
from kyc_engine.ocr.cropper import DocumentCropper
from kyc_engine.ocr.merger import SemanticMerger


def build_ocr_log(diagnostics: list[dict[str, str | bool]]) -> OCRLog:
    local_success = any(
        bool(item.get("success"))
        and str(item.get("source", "")).strip() in {"tesseract", "fallback"}
        for item in diagnostics
    )
    gemini_success = any(
        bool(item.get("success")) and str(item.get("source", "")).strip() == "gemini"
        for item in diagnostics
    )
    failed_sources = sorted(
        {
            str(item.get("source", "")).strip()
            for item in diagnostics
            if not bool(item.get("success"))
            and str(item.get("source", "")).strip() not in {"", "fallback", "none"}
        }
    )
    successful_sources = [
        item
        for item in diagnostics
        if bool(item.get("success")) and str(item.get("source", "")).strip()
    ]

    if successful_sources and not failed_sources:
        return OCRLog(
            status="SUCCESS",
            message="OCR processed successfully",
            failure_location=None,
        )

    if successful_sources and failed_sources:
        failure_location = ", ".join(failed_sources)
        if local_success and not gemini_success:
            return OCRLog(
                status="PARTIAL",
                message="OCR completed using local fallback extraction",
                failure_location=failure_location,
            )
        return OCRLog(
            status="PARTIAL",
            message=f"OCR completed with provider issues from: {failure_location}",
            failure_location=failure_location,
        )

    fallback_success = any(
        bool(item.get("success")) and str(item.get("source")) == "fallback"
        for item in diagnostics
    )
    if fallback_success:
        return OCRLog(
            status="PARTIAL",
            message="OCR completed using fallback extraction",
            failure_location="primary_ocr",
        )

    if diagnostics:
        failure_location = ", ".join(
            sorted(
                {
                    str(item.get("source", "")).strip()
                    for item in diagnostics
                    if str(item.get("source", "")).strip()
                }
            )
        ) or "ocr"
    else:
        failure_location = "ocr"

    return OCRLog(
        status="FAILED",
        message="OCR failed",
        failure_location=failure_location,
    )


class OCRExtractor:
    GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    FOCUS_FIELDS = {
        "pan": ["pan_number", "pan_name", "pan_dob", "pan_father_name"],
        "aadhaar": ["aadhaar_name", "aadhaar_address"],
        "statement": [
            "statement_name",
            "statement_account_number",
            "statement_ifsc_code",
            "statement_address",
        ],
    }

    @staticmethod
    def _build_ocr_log(diagnostics: list[dict[str, str | bool]]) -> OCRLog:
        return build_ocr_log(diagnostics)

    def __init__(self) -> None:
        self.parser = OCRParser()
        self.cropper = DocumentCropper()
        self.merger = SemanticMerger(self.parser)

    async def extract(
        self,
        files: dict[str, FilePayload],
        audit_trail: list[AuditEntry],
    ) -> tuple[OCRBundle, OCRLog]:
        from kyc_engine.ocr.gemini_extractor import GeminiKYCExtractor
        import asyncio

        settings = get_settings()
        if not settings.gemini_configured:
            # Fallback to local
            return await self._old_extract(files, audit_trail)

        gemini_extractor = GeminiKYCExtractor(api_key=settings.gemini_api_key)
        diagnostics = [{"document": "all", "source": "gemini", "success": True}]
        
        try:
            result = await asyncio.to_thread(
                gemini_extractor.extract_all,
                pan_bytes=files["pan_file"].data,
                aadhaar_bytes=files["aadhaar_file"].data,
                bank_bytes=files["bank_statement"].data,
                pan_mime=files["pan_file"].content_type,
                aadhaar_mime=files["aadhaar_file"].content_type,
                bank_mime=files["bank_statement"].content_type,
            )
        except Exception as exc:
            diagnostics[0]["success"] = False
            diagnostics[0]["failure"] = str(exc)
            audit_trail.append(
                AuditEntry(
                    level="ERROR",
                    stage="OCR",
                    message=f"Gemini API error: {exc}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            return await self._old_extract(files, audit_trail)

        extracted = {
            "pan_details": {
                "pan_number": result.get("pan", {}).get("pan_number", ""),
                "pan_name": result.get("pan", {}).get("name", ""),
                "pan_dob": result.get("pan", {}).get("dob", ""),
                "pan_father_name": result.get("pan", {}).get("father_name", ""),
                "pan_signature_path": files["pan_file"].filename,
            },
            "aadhaar_details": {
                "aadhaar_number": result.get("aadhaar", {}).get("aadhaar_number", ""),
                "aadhaar_name": result.get("aadhaar", {}).get("name", ""),
                "aadhaar_dob": result.get("aadhaar", {}).get("dob", ""),
                "aadhaar_address": result.get("aadhaar", {}).get("address", ""),
            },
            "statement_details": {
                "statement_name": result.get("bank", {}).get("account_holder", ""),
                "statement_account_number": result.get("bank", {}).get("account_number", ""),
                "statement_ifsc_code": result.get("bank", {}).get("ifsc", ""),
                "statement_address": result.get("bank", {}).get("address", ""),
            },
            "signature_details": {
                "signature_live_path": files["live_signature"].filename,
            },
        }

        # Handle None values
        for section in extracted.values():
            for k, v in section.items():
                if v is None:
                    section[k] = ""

        ocr_log = build_ocr_log(diagnostics)
        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="OCR",
                message="Extracted documents using GeminiKYCExtractor",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return OCRBundle.model_validate(extracted), ocr_log

    async def _old_extract(
        self,
        files: dict[str, FilePayload],
        audit_trail: list[AuditEntry],
    ) -> tuple[OCRBundle, OCRLog]:
        diagnostics: list[dict[str, str | bool]] = []
        extracted = {
            "pan_details": self._extract_document(
                "pan", files["pan_file"], audit_trail, diagnostics
            ),
            "aadhaar_details": self._extract_document(
                "aadhaar", files["aadhaar_file"], audit_trail, diagnostics
            ),
            "statement_details": self._extract_document(
                "statement", files["bank_statement"], audit_trail, diagnostics
            ),
            "signature_details": {
                "signature_live_path": files["live_signature"].filename,
            },
        }
        extracted["pan_details"]["pan_signature_path"] = files["pan_file"].filename

        ocr_log = build_ocr_log(diagnostics)
        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="OCR",
                message=ocr_log.message,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return OCRBundle.model_validate(extracted), ocr_log

    def refine_statement_holder_name(
        self,
        statement_payload: FilePayload,
        current_statement_name: str,
        holder_names: list[str],
        audit_trail: list[AuditEntry],
    ) -> str:
        # Refinement is now handled internally by GeminiKYCExtractor
        return current_statement_name


    def _extract_document(
        self,
        document_type: str,
        file_payload: FilePayload,
        audit_trail: list[AuditEntry],
        diagnostics: list[dict[str, str | bool]],
    ) -> dict:
        settings = get_settings()
        
        if not settings.ocr_providers_available:
            diagnostics.append({"document": document_type, "source": "none", "success": False, "failure": "No OCR providers configured"})
            audit_trail.append(AuditEntry(level="ERROR", stage="OCR", message=f"{document_type}: No OCR providers configured", timestamp=datetime.now(timezone.utc).isoformat()))
            parsed, fallback_source = self._extract_with_fallback(document_type, file_payload, settings)
            diagnostics.append({"document": document_type, "source": fallback_source, "success": any(bool(str(value).strip()) for value in parsed.values()), "failure": ""})
            return parsed
        
        candidates: list[dict] = []
        provider_attempts = [
            ("gemini", settings.gemini_configured, lambda: self._extract_with_openai_compatible(
                endpoint=self.GEMINI_ENDPOINT,
                api_key=settings.gemini_api_key,
                model=settings.gemini_vision_model,
                document_type=document_type,
                file_payload=file_payload,
            )),
        ]

        for provider_name, configured, extractor in provider_attempts:
            if not configured:
                diagnostics.append({"document": document_type, "source": provider_name, "success": False, "failure": f"{provider_name} is not configured"})
                continue

            try:
                parsed = self._retry_call(extractor, retries=2, delay=1.0)
                candidates.append(parsed)
                diagnostics.append({"document": document_type, "source": provider_name, "success": True, "failure": ""})
            except Exception as exc:
                diagnostics.append({"document": document_type, "source": provider_name, "success": False, "failure": str(exc)})
                audit_trail.append(AuditEntry(level="WARNING", stage="OCR", message=f"{document_type}: {provider_name} OCR failed ({exc})", timestamp=datetime.now(timezone.utc).isoformat()))

        if not candidates:
            parsed, fallback_source = self._extract_with_fallback(document_type, file_payload, settings)
            diagnostics.append({"document": document_type, "source": fallback_source, "success": any(bool(str(value).strip()) for value in parsed.values()), "failure": ""})
            return parsed

        merged = self.merger.merge_candidates(document_type, candidates)
        merged = self._recover_missing_fields_with_focus_pass(document_type, merged, file_payload, settings, audit_trail, diagnostics)
        return merged

    def _recover_missing_fields_with_focus_pass(
        self,
        document_type: str,
        parsed: dict,
        file_payload: FilePayload,
        settings,
        audit_trail: list[AuditEntry],
        diagnostics: list[dict[str, str | bool]],
    ) -> dict:
        missing_fields = [f for f in self.FOCUS_FIELDS.get(document_type, []) if not str(parsed.get(f, "")).strip()]
        if not missing_fields:
            return parsed

        merged = parsed.copy()
        if settings.tesseract_available and pytesseract is not None:
            tesseract_focused = self._extract_focus_with_tesseract(document_type, missing_fields, file_payload, settings)
            if any(str(tesseract_focused.get(field, "")).strip() for field in missing_fields):
                merged = self.merger.merge_missing_fields(merged, tesseract_focused)
                diagnostics.append({"document": document_type, "source": "tesseract-focus", "success": True, "failure": ""})

        missing_fields = [f for f in self.FOCUS_FIELDS.get(document_type, []) if not str(merged.get(f, "")).strip()]
        if not missing_fields:
            return merged

        if not self._provider_rate_limited(diagnostics, "gemini"):
            try:
                focused = self._extract_focus_with_provider(
                    endpoint=self.GEMINI_ENDPOINT,
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_vision_model,
                    document_type=document_type,
                    fields=missing_fields,
                    file_payload=file_payload,
                )
                diagnostics.append({"document": document_type, "source": "gemini-focus", "success": True, "failure": ""})
                merged = self.merger.merge_missing_fields(merged, focused)
            except Exception as exc:
                diagnostics.append({"document": document_type, "source": "gemini-focus", "success": False, "failure": str(exc)})

        return merged

    def _extract_focus_with_provider(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        document_type: str,
        fields: list[str],
        file_payload: FilePayload,
    ) -> dict:
        prompt = self.parser.build_focus_prompt(document_type, fields)
        content: list[dict] = [{"type": "text", "text": prompt}]
        image_data_uri = self.cropper.to_image_data_uri(file_payload, document_type)
        if image_data_uri:
            content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
        if file_payload.extension == ".pdf":
            content.append({"type": "text", "text": f"Document text:\n{self._extract_pdf_text(file_payload.data)}"})

        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": "You are an OCR transcriber. Extract only requested fields into valid JSON."},
                    {"role": "user", "content": content},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        return self.parser.parse_partial({field: "" for field in fields}, raw)

    def _extract_with_openai_compatible(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        document_type: str,
        file_payload: FilePayload,
    ) -> dict:
        prompt = self.parser.build_prompt(document_type)
        content: list[dict] = [{"type": "text", "text": prompt}]
        image_data_uri = self.cropper.to_image_data_uri(file_payload, document_type)
        if image_data_uri:
            content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
        if file_payload.extension == ".pdf":
            content.append({"type": "text", "text": f"Document text:\n{self._extract_pdf_text(file_payload.data)}"})

        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": "You are an OCR transcriber. Extract document details into valid JSON."},
                    {"role": "user", "content": content},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        return self.parser.parse_json(document_type, raw)

    def _extract_focus_with_tesseract(
        self,
        document_type: str,
        fields: list[str],
        file_payload: FilePayload,
        settings,
    ) -> dict:
        crops: dict[str, bytes] = {}
        if document_type == "statement":
            crops = self.cropper.render_statement_customer_crops(file_payload.data)
        elif document_type == "pan":
            crops = self.cropper.render_pan_focus_crops(file_payload)
        elif document_type == "aadhaar":
            crops = self.cropper.render_aadhaar_focus_crops(file_payload)

        candidates: list[dict] = []
        for name, image_bytes in crops.items():
            text = self._extract_text_from_image_bytes_with_tesseract(image_bytes, document_type, settings)
            if text:
                parsed = self.parser.parse_partial({f: "" for f in fields}, text)
                parsed["_source"] = f"tesseract-focus:{name}"
                candidates.append(parsed)
        
        return self.merger.merge_candidates(document_type, candidates) if candidates else self.parser.parse_partial({f: "" for f in fields}, "")

    def _extract_with_fallback(
        self,
        document_type: str,
        file_payload: FilePayload,
        settings,
    ) -> tuple[dict, str]:
        local_text = self._extract_with_tesseract(document_type, file_payload, settings)
        if local_text:
            parsed = self.parser.parse_text(document_type, local_text)
            if any(bool(str(value).strip()) for value in parsed.values()):
                return parsed, "tesseract"

        if file_payload.extension == ".pdf":
            return (self.parser.parse_fallback(document_type, self._extract_pdf_text(file_payload.data)), "fallback")
        return self.parser.empty_document(document_type), "fallback"

    def _extract_with_tesseract(
        self,
        document_type: str,
        file_payload: FilePayload,
        settings,
    ) -> str:
        if not settings.tesseract_available or pytesseract is None:
            return ""

        pytesseract.pytesseract.tesseract_cmd = settings.resolved_tesseract_cmd
        page_images = []
        if file_payload.extension == ".pdf":
            import fitz
            document = fitz.open(stream=file_payload.data, filetype="pdf")
            page_count = min(2, len(document))
            document.close()
            for i in range(page_count):
                img = self.cropper.open_document_image(file_payload, page_index=i)
                norm = self.cropper.normalize_image_for_ocr(img, document_type)
                buf = BytesIO()
                norm.save(buf, format="PNG")
                page_images.append(buf.getvalue())
        else:
            img = self.cropper.open_document_image(file_payload)
            norm = self.cropper.normalize_image_for_ocr(img, document_type)
            buf = BytesIO()
            norm.save(buf, format="PNG")
            page_images.append(buf.getvalue())

        outputs = []
        for image_bytes in page_images:
            text = self._extract_text_from_image_bytes_with_tesseract(image_bytes, document_type, settings)
            if text and text not in outputs:
                outputs.append(text)
        return "\n".join(outputs).strip()

    def _extract_text_from_image_bytes_with_tesseract(
        self,
        image_bytes: bytes,
        document_type: str,
        settings,
    ) -> str:
        if not settings.tesseract_available or pytesseract is None:
            return ""

        pytesseract.pytesseract.tesseract_cmd = settings.resolved_tesseract_cmd
        image = Image.open(BytesIO(image_bytes)).convert("L")
        array = np.array(image, dtype=np.uint8)
        array = cv2.resize(array, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        denoised = cv2.fastNlMeansDenoising(array, None, 12, 7, 21)
        blurred = cv2.GaussianBlur(denoised, (5, 5), 0)
        otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        adaptive = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)

        configs = {
            "pan": ["--oem 3 --psm 6", "--oem 3 --psm 11"],
            "aadhaar": ["--oem 3 --psm 6", "--oem 3 --psm 4"],
            "statement": ["--oem 3 --psm 6", "--oem 3 --psm 4", "--oem 3 --psm 11"],
        }
        outputs = []
        for candidate_image in [otsu, adaptive]:
            for config in configs.get(document_type, ["--oem 3 --psm 6"]):
                try:
                    text = pytesseract.image_to_string(candidate_image, config=config).strip()
                    if text and text not in outputs:
                        outputs.append(text)
                except Exception:
                    continue
        return "\n".join(outputs).strip()

    @staticmethod
    def _extract_pdf_text(data: bytes) -> str:
        from PyPDF2 import PdfReader
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise HTTPException(status_code=400, detail="File is password protected")
            return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Unable to extract PDF text: {exc}") from exc

    @staticmethod
    def _retry_call(callable_fn, retries: int = 2, delay: float = 1.0):
        last_error = None
        for attempt in range(retries + 1):
            try:
                return callable_fn()
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(delay * (attempt + 1))
        raise last_error or RuntimeError("Retry call failed")

    @staticmethod
    def _provider_rate_limited(diagnostics: list[dict[str, str | bool]], provider_prefix: str) -> bool:
        for item in diagnostics:
            if str(item.get("source", "")).startswith(provider_prefix) and ("429" in str(item.get("failure", "")) or "too many requests" in str(item.get("failure", "")).lower()):
                return True
        return False

    def _extract_statement_name_with_holder_context(self, payload: FilePayload, holders: list[str], settings) -> str:
        from kyc_engine.ocr.extractor import OCRExtractor
        prompt = f"Extract the customer name from this bank statement. Context: Likely holders are {holders}. Return ONLY a JSON object: {{\"statement_name\": \"...\"}}"
        content: list[dict] = [{"type": "text", "text": prompt}]
        image_data_uri = self.cropper.to_image_data_uri(payload, "statement")
        if image_data_uri:
            content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
        
        response = requests.post(
            self.GEMINI_ENDPOINT,
            headers={"Authorization": f"Bearer {settings.gemini_api_key}", "Content-Type": "application/json"},
            json={
                "model": settings.gemini_vision_model,
                "temperature": 0,
                "messages": [{"role": "user", "content": content}],
                "response_format": {"type": "json_object"},
            },
            timeout=30
        )
        response.raise_for_status()
        res = response.json()["choices"][0]["message"]["content"]
        return self.parser.parse_partial({"statement_name": ""}, res).get("statement_name", "")

    def _statement_name_candidates_from_tesseract(self, payload: FilePayload) -> list[str]:
        crops = self.cropper.render_statement_customer_crops(payload.data)
        candidates = []
        settings = get_settings()
        for name, img_bytes in crops.items():
            text = self._extract_text_from_image_bytes_with_tesseract(img_bytes, "statement", settings)
            if text:
                parsed = self.parser.parse_partial({"statement_name": ""}, text)
                if parsed.get("statement_name"):
                    candidates.append(parsed["statement_name"])
        return candidates
