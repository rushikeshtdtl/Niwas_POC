from datetime import datetime, timezone

from kyc_engine.config import get_rules
from kyc_engine.models.schema import AuditEntry, DecisionResult, MatchingResult


class DecisionEngine:
    def decide(
        self,
        final_score: float,
        matching: MatchingResult,
        audit_trail: list[AuditEntry],
    ) -> DecisionResult:
        rules = get_rules()
        if final_score < rules.thresholds["review"]:
            decision = "REJECT"
            reason = "Low consistency and/or high fraud penalties triggered rejection"
        elif matching.aadhaar_to_statement_address_score < rules.thresholds["address_review_floor"]:
            decision = "REVIEW"
            reason = "Address consistency is below the approval floor and requires manual review"
        elif final_score >= rules.thresholds["approve"]:
            decision = "APPROVE"
            reason = "High document consistency with acceptable signature match"
        else:
            decision = "REVIEW"
            reason = "Moderate consistency detected and manual review is required"

        audit_trail.append(
            AuditEntry(
                level="INFO",
                stage="DECISION",
                message=f"Decision = {decision}; reason = {reason}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return DecisionResult(decision_result=decision, decision_reason=reason)
