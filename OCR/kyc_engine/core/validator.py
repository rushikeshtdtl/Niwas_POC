import re
from datetime import datetime, timezone

from kyc_engine.models.schema import AuditEntry, ValidationResult


class ValidationEngine:
    PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
    AADHAAR_REGEX = re.compile(r"^\d{12}$")
    IFSC_REGEX = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
    DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def validate(self, normalized: dict, audit_trail: list[AuditEntry]) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        pan = normalized["pan_details"]
        aadhaar = normalized["aadhaar_details"]
        statement = normalized["statement_details"]
        signature = normalized["signature_details"]

        pan_valid = self._validate_pan(pan, errors)
        aadhaar_valid = self._validate_aadhaar(aadhaar, errors, warnings)
        statement_valid = self._validate_statement(statement, errors, warnings)
        signature_valid = bool(signature.get("signature_live_path"))

        if errors:
            audit_trail.append(
                AuditEntry(
                    level="WARNING",
                    stage="VALIDATION",
                    message=f"Validation issues: {'; '.join(errors)}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        if warnings:
            audit_trail.append(
                AuditEntry(
                    level="WARNING",
                    stage="VALIDATION",
                    message=f"Validation guidance: {'; '.join(warnings)}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="VALIDATION",
                message=(
                    "Validation completed"
                    if errors or warnings
                    else "PAN, Aadhaar, statement, and signature validation passed"
                ),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return ValidationResult(
            pan_validation_status=pan_valid,
            aadhaar_validation_status=aadhaar_valid,
            statement_validation_status=statement_valid,
            signature_validation_status=signature_valid,
            validation_errors=errors,
            validation_warnings=warnings,
        )

    def _validate_pan(self, pan: dict, errors: list[str]) -> bool:
        self._required(pan, ["pan_number", "pan_name", "pan_dob"], "pan_details", errors)
        if pan.get("pan_number") and not self.PAN_REGEX.match(pan["pan_number"]):
            errors.append("Invalid PAN format")
        if pan.get("pan_dob") and not self.DATE_REGEX.match(pan["pan_dob"]):
            errors.append("Invalid PAN DOB format")
        return not any(error.startswith("Missing required field: pan_details") or "PAN" in error for error in errors)

    def _validate_aadhaar(
        self,
        aadhaar: dict,
        errors: list[str],
        warnings: list[str],
    ) -> bool:
        self._required(
            aadhaar,
            ["aadhaar_number", "aadhaar_name", "aadhaar_dob"],
            "aadhaar_details",
            errors,
        )
        if not aadhaar.get("aadhaar_address"):
            if self._looks_like_aadhaar_front_side(aadhaar):
                warnings.append(
                    "Aadhaar address was not detected. This upload looks like the front side only. "
                    "Reupload Aadhaar with the address side as a PDF or a single combined front/back image."
                )
            else:
                errors.append("Missing required field: aadhaar_details.aadhaar_address")
        if aadhaar.get("aadhaar_number") and not self.AADHAAR_REGEX.match(aadhaar["aadhaar_number"]):
            errors.append("Invalid Aadhaar format")
        if aadhaar.get("aadhaar_dob") and not self.DATE_REGEX.match(aadhaar["aadhaar_dob"]):
            errors.append("Invalid Aadhaar DOB format")
        return not any(error.startswith("Missing required field: aadhaar_details") or "Aadhaar" in error for error in errors)

    def _validate_statement(
        self,
        statement: dict,
        errors: list[str],
        warnings: list[str],
    ) -> bool:
        self._required(
            statement,
            ["statement_name", "statement_account_number", "statement_ifsc_code", "statement_address"],
            "statement_details",
            errors,
        )
        if statement.get("statement_ifsc_code") and not self.IFSC_REGEX.match(statement["statement_ifsc_code"].upper()):
            errors.append("Invalid IFSC format")
        if not statement.get("statement_ifsc_code") or not statement.get("statement_address"):
            warnings.append(
                "Bank statement extraction is incomplete. Reupload a clearer statement page that shows the customer address and IFSC."
            )
        return not any(error.startswith("Missing required field: statement_details") or "IFSC" in error for error in errors)

    @staticmethod
    def _required(section: dict, fields: list[str], label: str, errors: list[str]) -> None:
        for field in fields:
            if not section.get(field):
                errors.append(f"Missing required field: {label}.{field}")

    @staticmethod
    def _looks_like_aadhaar_front_side(aadhaar: dict) -> bool:
        combined = " ".join(
            str(aadhaar.get(field, "") or "")
            for field in ["aadhaar_number", "aadhaar_name", "aadhaar_dob", "aadhaar_address"]
        ).lower()
        address_indicators = ["address", "s/o", "w/o", "d/o", "road", "street", "nagar", "pincode"]
        has_address_markers = any(indicator in combined for indicator in address_indicators)
        has_pincode = bool(re.search(r"\b\d{6}\b", combined))
        return not has_address_markers and not has_pincode
