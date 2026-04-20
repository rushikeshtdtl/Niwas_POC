import base64
import re
import time
from datetime import datetime, timezone
from io import BytesIO

import cv2
import fitz
import numpy as np
import requests
from fastapi import HTTPException
from PIL import Image, ImageFilter, ImageOps
from PyPDF2 import PdfReader

try:
    import pytesseract
except ImportError:  # pragma: no cover - depends on local runtime
    pytesseract = None

from kyc_engine.config import get_settings
from kyc_engine.core.file_validator import FilePayload
from kyc_engine.models.schema import AuditEntry, OCRBundle, OCRLog
from kyc_engine.ocr.parser import OCRParser
from kyc_engine.utils.similarity import name_similarity


def build_ocr_log(diagnostics: list[dict[str, str | bool]]) -> OCRLog:
    local_success = any(
        bool(item.get("success"))
        and str(item.get("source", "")).strip() in {"tesseract", "fallback"}
        for item in diagnostics
    )
    groq_success = any(
        bool(item.get("success")) and str(item.get("source", "")).strip() == "groq"
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
        if local_success and not groq_success:
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
    GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
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
    FIELD_PRIORITY = {
        "pan_number": "id",
        "aadhaar_number": "id",
        "statement_account_number": "account",
        "statement_ifsc_code": "ifsc",
        "pan_name": "name",
        "aadhaar_name": "name",
        "statement_name": "name",
        "pan_father_name": "name",
        "pan_dob": "date",
        "aadhaar_dob": "date",
        "aadhaar_address": "address",
        "statement_address": "address",
        "pan_signature_path": "path",
        "signature_live_path": "path",
    }
    STATEMENT_BANK_MARKERS = {
        "bank",
        "branch",
        "customer care",
        "customercare",
        "help line",
        "helpline",
        "ifsc",
        "micr",
        "email",
        "phone",
        "fax",
        "www.",
        "ltd",
        "limited",
    }

    def __init__(self) -> None:
        self.parser = OCRParser()

    @staticmethod
    def _build_ocr_log(diagnostics: list[dict[str, str | bool]]) -> OCRLog:
        """
        Backward-compatible alias for older call sites that referenced
        an instance helper instead of the module-level builder.
        """
        return build_ocr_log(diagnostics)

    async def extract(
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
        normalized_holders = [name.strip().upper() for name in holder_names if name.strip()]
        if not normalized_holders:
            return current_statement_name

        current_name = current_statement_name.strip().upper()
        current_score = self._best_holder_name_score(current_name, normalized_holders)
        if current_name and current_score >= 85:
            return current_statement_name

        candidate_names = self._statement_name_candidates_from_tesseract(
            statement_payload
        )
        best_local = self._pick_best_holder_aligned_name(
            candidate_names,
            normalized_holders,
        )
        if best_local and self._best_holder_name_score(best_local, normalized_holders) > current_score:
            audit_trail.append(
                AuditEntry(
                    level="INFO",
                    stage="OCR",
                    message=(
                        "statement: holder-aware local refinement improved statement_name "
                        f"from '{current_statement_name}' to '{best_local}'"
                    ),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            return best_local

        settings = get_settings()
        if not settings.groq_configured:
            return current_statement_name

        ai_candidate = self._extract_statement_name_with_holder_context(
            statement_payload,
            normalized_holders,
            settings,
        )
        if ai_candidate and self._best_holder_name_score(ai_candidate, normalized_holders) > current_score:
            audit_trail.append(
                AuditEntry(
                    level="INFO",
                    stage="OCR",
                    message=(
                        "statement: holder-aware AI refinement improved statement_name "
                        f"from '{current_statement_name}' to '{ai_candidate}'"
                    ),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            return ai_candidate

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
            diagnostics.append(
                {
                    "document": document_type,
                    "source": "none",
                    "success": False,
                    "failure": "No OCR providers configured",
                }
            )
            audit_trail.append(
                AuditEntry(
                    level="ERROR",
                    stage="OCR",
                    message=f"{document_type}: No OCR providers configured (Groq/Tesseract)",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            parsed, fallback_source = self._extract_with_fallback(
                document_type, file_payload, settings
            )
            diagnostics.append(
                {
                    "document": document_type,
                    "source": fallback_source,
                    "success": any(bool(str(value).strip()) for value in parsed.values()),
                    "failure": "local fallback returned empty fields"
                    if not any(bool(str(value).strip()) for value in parsed.values())
                    else "",
                }
            )
            return parsed
        
        candidates: list[dict] = []

        provider_attempts = [
            (
                "groq",
                settings.groq_configured,
                lambda: self._extract_with_openai_compatible(
                    endpoint=self.GROQ_ENDPOINT,
                    api_key=settings.groq_api_key,
                    model=settings.groq_vision_model,
                    document_type=document_type,
                    file_payload=file_payload,
                ),
            ),
        ]

        for provider_name, configured, extractor in provider_attempts:
            if not configured:
                diagnostics.append(
                    {
                        "document": document_type,
                        "source": provider_name,
                        "success": False,
                        "failure": f"{provider_name} is not configured",
                    }
                )
                audit_trail.append(
                    AuditEntry(
                        level="WARNING",
                        stage="OCR",
                        message=f"{document_type}: {provider_name} OCR skipped because it is not configured",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
                continue

            try:
                parsed = self._retry_call(extractor, retries=2, delay=1.0)
                candidates.append(parsed)
                diagnostics.append(
                    {
                        "document": document_type,
                        "source": provider_name,
                        "success": True,
                        "failure": "",
                    }
                )
                audit_trail.append(
                    AuditEntry(
                        level="INFO",
                        stage="OCR",
                        message=f"{document_type}: {provider_name} OCR extraction succeeded",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
            except Exception as exc:
                diagnostics.append(
                    {
                        "document": document_type,
                        "source": provider_name,
                        "success": False,
                        "failure": str(exc),
                    }
                )
                audit_trail.append(
                    AuditEntry(
                        level="WARNING",
                        stage="OCR",
                        message=f"{document_type}: {provider_name} OCR failed ({exc})",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )

        if not candidates:
            parsed, fallback_source = self._extract_with_fallback(
                document_type, file_payload, settings
            )
            diagnostics.append(
                {
                    "document": document_type,
                    "source": fallback_source,
                    "success": any(
                        bool(str(value).strip()) for value in parsed.values()
                    ),
                    "failure": f"{fallback_source} returned empty fields"
                    if not any(bool(str(value).strip()) for value in parsed.values())
                    else "",
                }
            )
            audit_trail.append(
                AuditEntry(
                    level="WARNING",
                    stage="OCR",
                    message=f"{document_type}: {fallback_source} extraction completed",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            return parsed

        parsed = self._semantic_merge_candidates(document_type, candidates)
        parsed = self._recover_missing_fields_with_focus_pass(
            document_type,
            parsed,
            file_payload,
            settings,
            audit_trail,
            diagnostics,
        )
        return parsed

    def _extract_statement_customer_candidates(
        self,
        file_payload: FilePayload,
        settings,
        diagnostics: list[dict[str, str | bool]],
        audit_trail: list[AuditEntry],
        fields: list[str],
    ) -> list[dict]:
        if file_payload.extension != ".pdf":
            return []
        if self._provider_rate_limited(diagnostics, "groq"):
            return []

        region_candidates: list[dict] = []
        crops = self._render_statement_customer_crops(file_payload.data)
        focus_attempts = [
            (
                "groq-statement-customer-focus",
                settings.groq_configured,
                settings.groq_api_key,
                settings.groq_vision_model,
                self.GROQ_ENDPOINT,
            ),
        ]

        for provider_name, configured, api_key, model, endpoint in focus_attempts:
            if not configured:
                continue
            for crop_name, crop_bytes in crops.items():
                try:
                    focused = self._extract_focus_from_image_bytes(
                        endpoint=endpoint,
                        api_key=api_key,
                        model=model,
                        document_type="statement",
                        fields=fields,
                        image_bytes=crop_bytes,
                    )
                    focused["_source"] = f"{provider_name}:{crop_name}"
                    region_candidates.append(focused)
                    diagnostics.append(
                        {
                            "document": "statement",
                            "source": f"{provider_name}:{crop_name}",
                            "success": True,
                            "failure": "",
                        }
                    )
                except Exception as exc:
                    diagnostics.append(
                        {
                            "document": "statement",
                            "source": f"{provider_name}:{crop_name}",
                            "success": False,
                            "failure": str(exc),
                        }
                    )
                    audit_trail.append(
                        AuditEntry(
                            level="WARNING",
                            stage="OCR",
                            message=f"statement: {provider_name}:{crop_name} recovery failed ({exc})",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                    )
        return region_candidates

    def _extract_pan_focus_candidates(
        self,
        file_payload: FilePayload,
        settings,
        diagnostics: list[dict[str, str | bool]],
        audit_trail: list[AuditEntry],
        fields: list[str],
    ) -> list[dict]:
        region_candidates: list[dict] = []
        if self._provider_rate_limited(diagnostics, "groq"):
            return []
        focus_attempts = [
            (
                "groq-pan-focus",
                settings.groq_configured,
                settings.groq_api_key,
                settings.groq_vision_model,
                self.GROQ_ENDPOINT,
            ),
        ]

        for provider_name, configured, api_key, model, endpoint in focus_attempts:
            if not configured:
                continue
            for crop_name, crop_bytes in self._render_pan_focus_crops(file_payload).items():
                try:
                    focused = self._extract_focus_from_image_bytes(
                        endpoint=endpoint,
                        api_key=api_key,
                        model=model,
                        document_type="pan",
                        fields=fields,
                        image_bytes=crop_bytes,
                    )
                    focused["_source"] = f"{provider_name}:{crop_name}"
                    region_candidates.append(focused)
                    diagnostics.append(
                        {
                            "document": "pan",
                            "source": f"{provider_name}:{crop_name}",
                            "success": True,
                            "failure": "",
                        }
                    )
                except Exception as exc:
                    diagnostics.append(
                        {
                            "document": "pan",
                            "source": f"{provider_name}:{crop_name}",
                            "success": False,
                            "failure": str(exc),
                        }
                    )
                    audit_trail.append(
                        AuditEntry(
                            level="WARNING",
                            stage="OCR",
                            message=f"pan: {provider_name}:{crop_name} recovery failed ({exc})",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                    )
        return region_candidates

    def _extract_aadhaar_focus_candidates(
        self,
        file_payload: FilePayload,
        settings,
        diagnostics: list[dict[str, str | bool]],
        audit_trail: list[AuditEntry],
        fields: list[str],
    ) -> list[dict]:
        region_candidates: list[dict] = []
        if self._provider_rate_limited(diagnostics, "groq"):
            return []
        focus_attempts = [
            (
                "groq-aadhaar-address-focus",
                settings.groq_configured,
                settings.groq_api_key,
                settings.groq_vision_model,
                self.GROQ_ENDPOINT,
            ),
        ]

        for provider_name, configured, api_key, model, endpoint in focus_attempts:
            if not configured:
                continue
            for crop_name, crop_bytes in self._render_aadhaar_focus_crops(file_payload).items():
                try:
                    focused = self._extract_focus_from_image_bytes(
                        endpoint=endpoint,
                        api_key=api_key,
                        model=model,
                        document_type="aadhaar",
                        fields=fields,
                        image_bytes=crop_bytes,
                    )
                    focused["_source"] = f"{provider_name}:{crop_name}"
                    region_candidates.append(focused)
                    diagnostics.append(
                        {
                            "document": "aadhaar",
                            "source": f"{provider_name}:{crop_name}",
                            "success": True,
                            "failure": "",
                        }
                    )
                except Exception as exc:
                    diagnostics.append(
                        {
                            "document": "aadhaar",
                            "source": f"{provider_name}:{crop_name}",
                            "success": False,
                            "failure": str(exc),
                        }
                    )
                    audit_trail.append(
                        AuditEntry(
                            level="WARNING",
                            stage="OCR",
                            message=f"aadhaar: {provider_name}:{crop_name} recovery failed ({exc})",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                    )
        return region_candidates

    def _recover_missing_fields_with_focus_pass(
        self,
        document_type: str,
        parsed: dict,
        file_payload: FilePayload,
        settings,
        audit_trail: list[AuditEntry],
        diagnostics: list[dict[str, str | bool]],
    ) -> dict:
        missing_fields = self._missing_focus_fields(document_type, parsed)
        if not missing_fields:
            return parsed

        merged = parsed.copy()
        if settings.tesseract_available and pytesseract is not None:
            tesseract_focused = self._extract_focus_with_tesseract(
                document_type,
                missing_fields,
                file_payload,
                settings,
            )
            if any(
                str(tesseract_focused.get(field, "")).strip()
                for field in missing_fields
            ):
                merged = self._merge_missing_fields(merged, tesseract_focused)
                diagnostics.append(
                    {
                        "document": document_type,
                        "source": "tesseract-focus",
                        "success": True,
                        "failure": "",
                    }
                )
                recovered_local = [
                    field
                    for field in missing_fields
                    if str(merged.get(field, "")).strip()
                ]
                if recovered_local:
                    audit_trail.append(
                        AuditEntry(
                            level="INFO",
                            stage="OCR",
                            message=(
                                f"{document_type}: local focused OCR recovered fields "
                                f"{recovered_local}"
                            ),
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                    )
            else:
                diagnostics.append(
                    {
                        "document": document_type,
                        "source": "tesseract-focus",
                        "success": False,
                        "failure": "tesseract focus returned empty fields",
                    }
                )

        missing_fields = self._missing_focus_fields(document_type, merged)
        if not missing_fields:
            return merged

        focus_attempts = [
            (
                "groq-focus",
                settings.groq_configured,
                settings.groq_api_key,
                settings.groq_vision_model,
                self.GROQ_ENDPOINT,
            ),
        ]

        for provider_name, configured, api_key, model, endpoint in focus_attempts:
            if not configured:
                continue
            if self._provider_rate_limited(diagnostics, "groq"):
                break
            try:
                focused = self._extract_focus_with_provider(
                    endpoint=endpoint,
                    api_key=api_key,
                    model=model,
                    document_type=document_type,
                    fields=missing_fields,
                    file_payload=file_payload,
                )
                diagnostics.append(
                    {
                        "document": document_type,
                        "source": provider_name,
                        "success": True,
                        "failure": "",
                    }
                )
                merged = self._merge_missing_fields(merged, focused)
                recovered_remote = [
                    field
                    for field in missing_fields
                    if str(merged.get(field, "")).strip()
                ]
                if recovered_remote:
                    audit_trail.append(
                        AuditEntry(
                            level="INFO",
                            stage="OCR",
                            message=(
                                f"{document_type}: final AI recovery filled fields "
                                f"{recovered_remote}"
                            ),
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                    )
                    break
            except Exception as exc:
                diagnostics.append(
                    {
                        "document": document_type,
                        "source": provider_name,
                        "success": False,
                        "failure": str(exc),
                    }
                )
                audit_trail.append(
                    AuditEntry(
                        level="WARNING",
                        stage="OCR",
                        message=f"{document_type}: {provider_name} recovery failed ({exc})",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )

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
        image_data_uri = self._to_image_data_uri(file_payload, document_type)
        if image_data_uri:
            content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
        if file_payload.extension == ".pdf":
            content.append(
                {
                    "type": "text",
                    "text": f"Document text:\n{self._extract_pdf_text(file_payload.data)}",
                }
            )

        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an OCR transcriber. Extract only the requested visible fields into valid JSON.",
                    },
                    {"role": "user", "content": content},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        return self.parser.parse_partial({field: "" for field in fields}, raw)

    def _extract_focus_from_image_bytes(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        document_type: str,
        fields: list[str],
        image_bytes: bytes,
    ) -> dict:
        prompt = self.parser.build_focus_prompt(document_type, fields)
        content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": self._image_bytes_to_data_uri(image_bytes)},
            },
        ]
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an OCR transcriber. Extract only the requested visible fields into valid JSON.",
                    },
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
        image_data_uri = self._to_image_data_uri(file_payload, document_type)
        if image_data_uri:
            content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
        if file_payload.extension == ".pdf":
            content.append(
                {
                    "type": "text",
                    "text": f"Document text:\n{self._extract_pdf_text(file_payload.data)}",
                }
            )

        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an OCR transcriber. Extract only visible text into valid JSON.",
                    },
                    {"role": "user", "content": content},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        return self.parser.parse(document_type, raw)

    def _extract_focus_with_tesseract(
        self,
        document_type: str,
        fields: list[str],
        file_payload: FilePayload,
        settings,
    ) -> dict:
        crop_renderers = {
            "pan": lambda: self._render_pan_focus_crops(file_payload),
            "aadhaar": lambda: self._render_aadhaar_focus_crops(file_payload),
            "statement": lambda: self._render_statement_customer_crops(file_payload.data)
            if file_payload.extension == ".pdf"
            else {
                "statement-full": self._document_image_bytes_for_ocr(
                    file_payload, "statement"
                )
            },
        }
        renderer = crop_renderers.get(document_type)
        if renderer is None:
            return {field: "" for field in fields}

        candidates: list[dict] = []
        for crop_bytes in renderer().values():
            text = self._extract_text_from_image_bytes_with_tesseract(
                crop_bytes, document_type, settings
            )
            if not text:
                continue
            candidates.append(self.parser.parse_text(document_type, text))

        if not candidates:
            return {field: "" for field in fields}

        merged = self._semantic_merge_candidates(document_type, candidates)
        return {field: str(merged.get(field, "")).strip() for field in fields}

    def _statement_name_candidates_from_tesseract(
        self,
        statement_payload: FilePayload,
    ) -> list[str]:
        settings = get_settings()
        if not settings.tesseract_available or pytesseract is None:
            return []

        if statement_payload.extension == ".pdf":
            crop_map = self._render_statement_customer_crops(statement_payload.data)
        else:
            crop_map = {
                "statement-full": self._document_image_bytes_for_ocr(
                    statement_payload, "statement"
                )
            }

        candidates: list[str] = []
        for crop_bytes in crop_map.values():
            text = self._extract_text_from_image_bytes_with_tesseract(
                crop_bytes,
                "statement",
                settings,
            )
            if not text:
                continue
            name = self.parser.parse_text("statement", text).get("statement_name", "").strip()
            if name:
                candidates.append(name.upper())
        return candidates

    def _extract_statement_name_with_holder_context(
        self,
        statement_payload: FilePayload,
        holder_names: list[str],
        settings,
    ) -> str:
        holder_hint = ", ".join(holder_names)
        prompt = (
            "Extract only the bank statement account-holder/customer name as JSON using this schema: "
            '{"statement_name":""}. '
            "Do not return father name, nominee name, address text, branch name, or bank name. "
            f"The correct holder name should closely match one of these known KYC holder names: {holder_hint}."
        )
        content: list[dict] = [{"type": "text", "text": prompt}]
        image_data_uri = self._to_image_data_uri(statement_payload, "statement")
        if image_data_uri:
            content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
        if statement_payload.extension == ".pdf":
            content.append(
                {
                    "type": "text",
                    "text": f"Document text:\n{self._extract_pdf_text(statement_payload.data)}",
                }
            )

        response = requests.post(
            self.GROQ_ENDPOINT,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_vision_model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an OCR transcriber. Extract only the requested visible field into valid JSON.",
                    },
                    {"role": "user", "content": content},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        parsed = self.parser.parse_partial({"statement_name": ""}, raw)
        return str(parsed.get("statement_name", "")).strip().upper()

    @staticmethod
    def _best_holder_name_score(candidate: str, holder_names: list[str]) -> float:
        if not candidate.strip():
            return 0.0
        return max((name_similarity(candidate, holder) for holder in holder_names), default=0.0)

    def _pick_best_holder_aligned_name(
        self,
        candidates: list[str],
        holder_names: list[str],
    ) -> str:
        best_candidate = ""
        best_score = 0.0
        for candidate in candidates:
            score = self._best_holder_name_score(candidate, holder_names)
            if score > best_score:
                best_candidate = candidate
                best_score = score
        return best_candidate if best_score >= 70 else ""

    def _semantic_merge_candidates(
        self, document_type: str, candidates: list[dict]
    ) -> dict:
        merged = self.parser.empty_document(document_type)
        for field in merged:
            best_value = ""
            best_score = -1
            for candidate in candidates:
                value = str(candidate.get(field, "") or "").strip()
                score = self._score_field_value(
                    field, value, str(candidate.get("_source", ""))
                )
                if score > best_score:
                    best_value = value
                    best_score = score
            merged[field] = best_value
        return merged

    def _missing_focus_fields(self, document_type: str, parsed: dict) -> list[str]:
        return [
            field
            for field in self.FOCUS_FIELDS.get(document_type, [])
            if not str(parsed.get(field, "")).strip()
        ]

    @staticmethod
    def _provider_rate_limited(
        diagnostics: list[dict[str, str | bool]],
        provider_prefix: str,
    ) -> bool:
        for item in diagnostics:
            source = str(item.get("source", "")).strip()
            failure = str(item.get("failure", "")).lower()
            if source.startswith(provider_prefix) and (
                "429" in failure or "too many requests" in failure
            ):
                return True
        return False

    @staticmethod
    def _merge_missing_fields(primary: dict, recovered: dict) -> dict:
        merged = primary.copy()
        for key, value in recovered.items():
            if not str(merged.get(key, "")).strip() and str(value).strip():
                merged[key] = str(value).strip()
        return merged

    def _score_field_value(self, field: str, value: str, source: str = "") -> int:
        text = value.strip()
        if not text:
            return 0

        category = self.FIELD_PRIORITY.get(field, "generic")
        if category == "address":
            tokens = len(text.split())
            has_pincode = bool(re.search(r"\b\d{6}\b", text))
            score = len(text) + (tokens * 3) + (50 if has_pincode else 0)
            if field == "statement_address":
                lowered = text.lower()
                if any(marker in lowered for marker in self.STATEMENT_BANK_MARKERS):
                    score -= 120
                if "customer-focus" in source or "customer_focus" in source:
                    score += 140
                if any(
                    token in lowered
                    for token in [
                        "apt",
                        "apartment",
                        "flat",
                        "society",
                        "nagar",
                        "galli",
                        "tal",
                        "dist",
                        "road",
                        "sector",
                        "plot",
                    ]
                ):
                    score += 20
            return score
        if category == "name":
            normalized = re.sub(
                r"\b(MR|MRS|MS|SMT|SHRI)\b\.?", "", text.upper()
            ).strip()
            score = len(normalized) + (len(normalized.split()) * 5)
            if field == "statement_name" and (
                "customer-focus" in source or "customer_focus" in source
            ):
                score += 40
            return score
        if category == "id":
            alnum = len(re.sub(r"[^A-Z0-9]", "", text.upper()))
            return alnum * 10
        if category == "account":
            digits = len(re.sub(r"\D", "", text))
            return digits * 10
        if category == "ifsc":
            return (
                100
                if re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", text.upper())
                else len(text)
            )
        if category == "date":
            return (
                100
                if re.fullmatch(r"\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2}", text)
                else len(text)
            )
        return len(text)

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
            return (
                self.parser.parse_fallback(
                    document_type, self._extract_pdf_text(file_payload.data)
                ),
                "fallback",
            )
        return self.parser.empty_document(document_type), "fallback"

    def _to_image_data_uri(
        self,
        file_payload: FilePayload,
        document_type: str,
        page_index: int = 0,
    ) -> str | None:
        try:
            image_bytes = self._document_image_bytes_for_ocr(
                file_payload, document_type, page_index=page_index
            )
        except Exception:
            return None
        return self._image_bytes_to_data_uri(image_bytes)

    @staticmethod
    def _image_bytes_to_data_uri(image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    @staticmethod
    def _render_pdf_to_png(data: bytes, page_index: int = 0) -> bytes:
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

    def _open_document_image(
        self,
        file_payload: FilePayload,
        page_index: int = 0,
    ) -> Image.Image:
        if file_payload.extension == ".pdf":
            image = Image.open(
                BytesIO(self._render_pdf_to_png(file_payload.data, page_index=page_index))
            )
        else:
            image = Image.open(BytesIO(file_payload.data))
        image = ImageOps.exif_transpose(image)
        return image.convert("RGB")

    def _document_image_bytes_for_ocr(
        self,
        file_payload: FilePayload,
        document_type: str,
        page_index: int = 0,
    ) -> bytes:
        image = self._open_document_image(file_payload, page_index=page_index)
        normalized = self._normalize_image_for_ocr(image, document_type)
        buffer = BytesIO()
        normalized.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _normalize_image_for_ocr(
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

    def _render_statement_customer_crops(self, data: bytes) -> dict[str, bytes]:
        rendered: dict[str, bytes] = {}
        document = fitz.open(stream=data, filetype="pdf")
        page_count = min(2, len(document))
        document.close()
        for page_index in range(page_count):
            full_image = self._normalize_image_for_ocr(
                self._open_document_image(
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

    def _render_pan_focus_crops(self, file_payload: FilePayload) -> dict[str, bytes]:
        image = self._normalize_image_for_ocr(
            self._open_document_image(file_payload),
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

    def _render_aadhaar_focus_crops(self, file_payload: FilePayload) -> dict[str, bytes]:
        image = self._normalize_image_for_ocr(
            self._open_document_image(file_payload),
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

    @staticmethod
    def _extract_pdf_text(data: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise HTTPException(status_code=400, detail="File is password protected")
            return "\n".join(
                (page.extract_text() or "") for page in reader.pages
            ).strip()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail=f"Unable to extract PDF text: {exc}"
            ) from exc

    @staticmethod
    def _retry_call(callable_fn, retries: int = 2, delay: float = 1.0):
        """
        Deterministic retry wrapper for transient OCR provider failures.
        Attempts = retries + 1, with linear sleep between retries.
        """
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return callable_fn()
            except Exception as exc:  # noqa: BLE001 - preserve upstream error surface
                last_error = exc
                if attempt < retries:
                    time.sleep(delay * (attempt + 1))
        if last_error is not None:
            raise last_error
        raise RuntimeError("Retry call failed without captured exception")

    def _extract_with_tesseract(
        self,
        document_type: str,
        file_payload: FilePayload,
        settings,
    ) -> str:
        if not settings.tesseract_available:
            return ""
        if pytesseract is None:
            return ""

        pytesseract.pytesseract.tesseract_cmd = settings.resolved_tesseract_cmd
        if file_payload.extension == ".pdf":
            document = fitz.open(stream=file_payload.data, filetype="pdf")
            page_count = min(2, len(document))
            document.close()
            page_images = [
                self._document_image_bytes_for_ocr(
                    file_payload,
                    document_type,
                    page_index=page_index,
                )
                for page_index in range(page_count)
            ]
        else:
            page_images = [self._document_image_bytes_for_ocr(file_payload, document_type)]

        outputs: list[str] = []
        for image_bytes in page_images:
            text = self._extract_text_from_image_bytes_with_tesseract(
                image_bytes,
                document_type,
                settings,
            )
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
        otsu = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]
        adaptive = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

        configs = {
            "pan": ["--oem 3 --psm 6", "--oem 3 --psm 11"],
            "aadhaar": ["--oem 3 --psm 6", "--oem 3 --psm 4"],
            "statement": ["--oem 3 --psm 6", "--oem 3 --psm 4", "--oem 3 --psm 11"],
        }
        outputs: list[str] = []
        for candidate_image in [otsu, adaptive]:
            for config in configs.get(document_type, ["--oem 3 --psm 6"]):
                try:
                    text = pytesseract.image_to_string(candidate_image, config=config).strip()
                except Exception:
                    continue
                if text and text not in outputs:
                    outputs.append(text)
        return "\n".join(outputs).strip()
