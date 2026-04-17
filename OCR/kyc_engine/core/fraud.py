from datetime import datetime, timezone

from kyc_engine.config import get_rules
from kyc_engine.models.schema import (
    AuditEntry,
    FraudBreakdownEntry,
    ForensicsResult,
    FraudResult,
    MatchingResult,
    ValidationResult,
)


class FraudEngine:
    def evaluate(
        self,
        validation: ValidationResult,
        matching: MatchingResult,
        audit_trail: list[AuditEntry],
        forensics: ForensicsResult | None = None,
    ) -> FraudResult:
        rules = get_rules()
        signals: list[str] = []
        breakdown: list[FraudBreakdownEntry] = []
        penalty_total = 0

        name_signal = self._tiered_score_signal(
            signal_prefix="name_mismatch",
            observed=matching.pan_to_aadhaar_name_score,
            mismatch_threshold=rules.thresholds["name_mismatch"],
            severe_threshold=rules.thresholds["name_severe_mismatch"],
            mild_penalty=rules.penalties["name_mismatch_minor"],
            severe_penalty=rules.penalties["name_mismatch_major"],
            detail=(
                f"PAN to Aadhaar name score {matching.pan_to_aadhaar_name_score} "
                f"fell below thresholds {rules.thresholds['name_mismatch']}/"
                f"{rules.thresholds['name_severe_mismatch']}"
            ),
        )
        if name_signal:
            signals.append(name_signal.signal)
            breakdown.append(name_signal)
            penalty_total += name_signal.penalty
        if not matching.pan_to_aadhaar_dob_match:
            signals.append("dob_mismatch")
            penalty_total += rules.penalties["dob_mismatch"]
            breakdown.append(
                FraudBreakdownEntry(
                    signal="dob_mismatch",
                    severity="HIGH",
                    penalty=rules.penalties["dob_mismatch"],
                    detail="PAN and Aadhaar DOB do not match exactly",
                )
            )
        address_signal = self._address_signal(validation, matching)
        if address_signal:
            signals.append(address_signal.signal)
            breakdown.append(address_signal)
            penalty_total += address_signal.penalty
        signature_signal = self._tiered_score_signal(
            signal_prefix="signature_mismatch",
            observed=matching.signature_match_score,
            mismatch_threshold=rules.thresholds["signature_mismatch"],
            severe_threshold=rules.thresholds["signature_severe_mismatch"],
            mild_penalty=rules.penalties["signature_mismatch_minor"],
            severe_penalty=rules.penalties["signature_mismatch_major"],
            detail=(
                f"Signature score {matching.signature_match_score} fell below thresholds "
                f"{rules.thresholds['signature_mismatch']}/"
                f"{rules.thresholds['signature_severe_mismatch']}"
            ),
        )
        if signature_signal:
            signals.append(signature_signal.signal)
            breakdown.append(signature_signal)
            penalty_total += signature_signal.penalty
        validation_flags = [
            validation.pan_validation_status,
            validation.aadhaar_validation_status,
            validation.statement_validation_status,
            validation.signature_validation_status,
        ]
        if not all(validation_flags):
            signals.append("invalid_field")
            invalid_count = len([flag for flag in validation_flags if not flag])
            invalid_penalty = min(
                rules.penalties["invalid_field_cap"],
                invalid_count * rules.penalties["invalid_field_per_document"],
            )
            penalty_total += invalid_penalty
            breakdown.append(
                FraudBreakdownEntry(
                    signal="invalid_field",
                    severity="HIGH" if invalid_count > 1 else "MEDIUM",
                    penalty=invalid_penalty,
                    detail=f"{invalid_count} document validation sections failed",
                )
            )
        if forensics:
            for signal in forensics.fraud_signals:
                if signal not in signals:
                    signals.append(signal)
                    penalty = rules.penalties.get(signal, 0)
                    if penalty:
                        penalty_total += penalty
                        breakdown.append(
                            FraudBreakdownEntry(
                                signal=signal,
                                severity="HIGH" if penalty >= 30 else "MEDIUM",
                                penalty=penalty,
                                detail="Image forensics triggered this document integrity signal",
                            )
                        )

        fraud_score = min(penalty_total, 100)
        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="FRAUD",
                message=(
                    f"Fraud score = {fraud_score}; signals = {signals or ['none']}; "
                    f"breakdown = {[item.model_dump() for item in breakdown] or ['none']}"
                ),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return FraudResult(
            fraud_score=fraud_score,
            fraud_signals=signals,
            fraud_breakdown=breakdown,
        )

    def _address_signal(
        self,
        validation: ValidationResult,
        matching: MatchingResult,
    ) -> FraudBreakdownEntry | None:
        rules = get_rules()
        if any(
            "Aadhaar address was not detected" in warning
            for warning in validation.validation_warnings
        ):
            return FraudBreakdownEntry(
                signal="address_data_incomplete",
                severity="LOW",
                penalty=rules.penalties["address_data_incomplete"],
                detail=(
                    "Aadhaar address is missing, likely because only the front side was uploaded. "
                    "Address comparison is incomplete."
                ),
            )

        return self._tiered_score_signal(
            signal_prefix="address_mismatch",
            observed=matching.aadhaar_to_statement_address_score,
            mismatch_threshold=rules.thresholds["address_mismatch"],
            severe_threshold=rules.thresholds["address_severe_mismatch"],
            mild_penalty=rules.penalties["address_mismatch_minor"],
            severe_penalty=rules.penalties["address_mismatch_major"],
            detail=(
                f"Aadhaar to statement address score "
                f"{matching.aadhaar_to_statement_address_score} fell below thresholds "
                f"{rules.thresholds['address_mismatch']}/"
                f"{rules.thresholds['address_severe_mismatch']}"
            ),
        )

    @staticmethod
    def _tiered_score_signal(
        signal_prefix: str,
        observed: float,
        mismatch_threshold: float,
        severe_threshold: float,
        mild_penalty: int,
        severe_penalty: int,
        detail: str,
    ) -> FraudBreakdownEntry | None:
        if observed >= mismatch_threshold:
            return None
        if observed < severe_threshold:
            return FraudBreakdownEntry(
                signal=f"{signal_prefix}_major",
                severity="HIGH",
                penalty=severe_penalty,
                detail=detail,
            )
        return FraudBreakdownEntry(
            signal=f"{signal_prefix}_minor",
            severity="MEDIUM",
            penalty=mild_penalty,
            detail=detail,
        )
