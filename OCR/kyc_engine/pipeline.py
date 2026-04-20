from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from kyc_engine.core.decision import DecisionEngine
from kyc_engine.core.file_validator import FileValidator
from kyc_engine.core.fraud import FraudEngine
from kyc_engine.core.image_forensics import ImageForensicsEngine
from kyc_engine.core.matcher import Matcher
from kyc_engine.core.normalizer import Normalizer
from kyc_engine.core.scorer import ScoringEngine
from kyc_engine.core.signature import SignatureComparator
from kyc_engine.core.validator import ValidationEngine
from kyc_engine.models.schema import (
    AuditEntry,
    KYCRequestFiles,
    KYCResponse,
    OCRBundle,
    OCRLog,
)
from kyc_engine.ocr.extractor import OCRExtractor


class KYCPipeline:
    def __init__(self) -> None:
        self.file_validator = FileValidator()
        self.ocr_extractor = OCRExtractor()
        self.normalizer = Normalizer()
        self.validator = ValidationEngine()
        self.matcher = Matcher()
        self.signature = SignatureComparator()
        self.forensics = ImageForensicsEngine()
        self.fraud = FraudEngine()
        self.scorer = ScoringEngine()
        self.decision = DecisionEngine()

    async def run(self, files: KYCRequestFiles) -> KYCResponse:
        audit_trail: list[AuditEntry] = []
        request_id = str(uuid4())

        validated_files = await self.file_validator.validate(files, audit_trail)
        forensics = self.forensics.analyze(validated_files, audit_trail)
        ocr_data, ocr_log = await self.ocr_extractor.extract(
            validated_files, audit_trail
        )
        holder_names = [
            ocr_data.pan_details.pan_name,
            ocr_data.aadhaar_details.aadhaar_name,
        ]
        ocr_data.statement_details.statement_name = self.ocr_extractor.refine_statement_holder_name(
            validated_files["bank_statement"],
            ocr_data.statement_details.statement_name,
            holder_names,
            audit_trail,
        )
        self._record_ocr_completeness(ocr_data.model_dump(), ocr_log, audit_trail)
        normalized = self.normalizer.normalize(ocr_data, audit_trail)
        validation = self.validator.validate(normalized, audit_trail)
        matching = self.matcher.match(normalized, audit_trail)
        try:
            matching.signature_match_score = self.signature.compare(
                validated_files["pan_file"],
                validated_files["live_signature"],
                audit_trail,
            )
        except ValueError as exc:
            self._raise_signature_error(str(exc), audit_trail)
        fraud_result = self.fraud.evaluate(
            validation,
            matching,
            audit_trail,
            forensics=forensics,
        )
        scoring = self.scorer.score(matching, fraud_result, audit_trail)
        decision = self.decision.decide(scoring.final_score, matching, audit_trail)

        return KYCResponse(
            request_id=request_id,
            kyc_status=decision.decision_result,
            kyc_scores=scoring,
            kyc_matching=matching,
            kyc_validation=validation,
            kyc_fraud=fraud_result,
            kyc_forensics=forensics,
            kyc_decision=decision,
            ocr_data=OCRBundle.model_validate(normalized),
            ocr_log=ocr_log,
            audit_trail=audit_trail,
            processed_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _record_ocr_completeness(
        self,
        ocr_data: dict,
        ocr_log: OCRLog,
        audit_trail: list[AuditEntry],
    ) -> list[str]:
        required_fields = {
            "pan_details": ["pan_number", "pan_name", "pan_dob"],
            "aadhaar_details": [
                "aadhaar_number",
                "aadhaar_name",
                "aadhaar_dob",
                "aadhaar_address",
            ],
            "statement_details": [
                "statement_name",
                "statement_account_number",
                "statement_ifsc_code",
                "statement_address",
            ],
            "signature_details": ["signature_live_path"],
        }
        missing_fields: list[str] = []
        for section, fields in required_fields.items():
            values = ocr_data.get(section, {})
            for field in fields:
                if not str(values.get(field, "")).strip():
                    missing_fields.append(f"{section}.{field}")

        if not missing_fields:
            return []

        ocr_log.status = "PARTIAL" if ocr_log.status != "FAILED" else "FAILED"
        ocr_log.message = (
            "OCR extracted partial data. Continue with review and consider reuploading clearer documents."
        )
        ocr_log.failure_location = ", ".join(missing_fields)
        message = (
            f"OCR missing fields: {', '.join(missing_fields)}. "
            "Continuing with partial extraction."
        )
        audit_trail.append(
            AuditEntry(
                level="WARNING",
                stage="OCR",
                message=message,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return missing_fields

    @staticmethod
    def _raise_signature_error(
        message: str,
        audit_trail: list[AuditEntry],
    ) -> None:
        audit_trail.append(
            AuditEntry(
                level="ERROR",
                stage="SIGNATURE",
                message=message,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        raise HTTPException(
            status_code=400,
            detail={
                "status": "ERROR",
                "stage": "SIGNATURE",
                "error": "Signature extraction failed",
                "errors": [message],
                "audit_trail": [entry.model_dump() for entry in audit_trail],
            },
        )
