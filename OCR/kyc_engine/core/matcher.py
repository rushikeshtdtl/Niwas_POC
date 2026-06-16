from datetime import datetime, timezone

from kyc_engine.models.schema import AuditEntry, MatchingResult
from kyc_engine.utils.similarity import address_similarity, name_similarity


class Matcher:
    def match(self, normalized: dict, audit_trail: list[AuditEntry]) -> MatchingResult:
        pan = normalized["pan_details"]
        aadhaar = normalized["aadhaar_details"]
        statement = normalized["statement_details"]

        pan_aadhaar = name_similarity(pan.get("pan_name", ""), aadhaar.get("aadhaar_name", ""))
        pan_statement = name_similarity(pan.get("pan_name", ""), statement.get("statement_name", ""))
        aadhaar_statement = name_similarity(aadhaar.get("aadhaar_name", ""), statement.get("statement_name", ""))
        address_score = address_similarity(aadhaar.get("aadhaar_address", ""), statement.get("statement_address", ""))
        dob_match = pan.get("pan_dob", "") == aadhaar.get("aadhaar_dob", "") and bool(pan.get("pan_dob"))

        for message in [
            f"PAN ↔ Aadhaar name match = {pan_aadhaar}",
            f"PAN ↔ Statement name match = {pan_statement}",
            f"Aadhaar ↔ Statement name match = {aadhaar_statement}",
            f"Aadhaar ↔ Statement address match = {address_score}",
            f"PAN ↔ Aadhaar DOB exact match = {dob_match}",
        ]:
            audit_trail.append(
                AuditEntry(
                    level="INFO",
                    stage="MATCHING",
                    message=message,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

        return MatchingResult(
            pan_to_aadhaar_name_score=pan_aadhaar,
            pan_to_statement_name_score=pan_statement,
            aadhaar_to_statement_name_score=aadhaar_statement,
            aadhaar_to_statement_address_score=address_score,
            pan_to_aadhaar_dob_match=dob_match,
            signature_match_score=0.0,
        )
