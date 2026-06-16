from datetime import datetime, timezone

from kyc_engine.config import get_rules
from kyc_engine.models.schema import AuditEntry, FraudResult, MatchingResult, ScoreResult


class ScoringEngine:
    def score(
        self,
        matching: MatchingResult,
        fraud: FraudResult,
        audit_trail: list[AuditEntry],
    ) -> ScoreResult:
        rules = get_rules()
        average_name_match = round(
            (
                matching.pan_to_aadhaar_name_score
                + matching.pan_to_statement_name_score
                + matching.aadhaar_to_statement_name_score
            )
            / 3,
            2,
        )
        identity_score = self._identity_score(average_name_match)
        risk_score = max(0, 100 - fraud.fraud_score)
        final_score = round(
            (identity_score * rules.identity_weight) + (risk_score * rules.fraud_weight),
            2,
        )

        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="SCORING",
                message=(
                    f"Average name match = {average_name_match}; identity score = {identity_score}; "
                    f"risk score = {risk_score}; final score = {final_score}"
                ),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return ScoreResult(
            identity_score=identity_score,
            fraud_score=fraud.fraud_score,
            risk_score=risk_score,
            signature_match_score=matching.signature_match_score,
            final_score=final_score,
        )

    @staticmethod
    def _identity_score(average_name_match: float) -> int:
        if average_name_match >= 90:
            return 100
        if average_name_match >= 75:
            return 70
        if average_name_match >= 50:
            return 40
        return 20
