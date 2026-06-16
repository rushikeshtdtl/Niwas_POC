import re
from kyc_engine.utils.similarity import name_similarity
from kyc_engine.config import get_rules


class SemanticMerger:
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

    def __init__(self, parser) -> None:
        self.parser = parser

    def merge_candidates(
        self, document_type: str, candidates: list[dict]
    ) -> dict:
        merged = self.parser.empty_document(document_type)
        for field in merged:
            best_value = ""
            best_score = -1
            for candidate in candidates:
                value = str(candidate.get(field, "") or "").strip()
                score = self.score_field_value(
                    field, value, str(candidate.get("_source", ""))
                )
                if score > best_score:
                    best_value = value
                    best_score = score
            merged[field] = best_value
        return merged

    def score_field_value(self, field: str, value: str, source: str = "") -> int:
        text = value.strip()
        if not text:
            return 0

        rules = get_rules()
        bank_markers = rules.ocr["statement_bank_markers"]
        
        category = self.FIELD_PRIORITY.get(field, "generic")
        if category == "address":
            tokens = len(text.split())
            has_pincode = bool(re.search(r"\b\d{6}\b", text))
            score = len(text) + (tokens * 3) + (50 if has_pincode else 0)
            if field == "statement_address":
                lowered = text.lower()
                if any(marker in lowered for marker in bank_markers):
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

    def pick_best_holder_aligned_name(
        self,
        candidates: list[str],
        holder_names: list[str],
    ) -> str:
        best_candidate = ""
        best_score = 0.0
        for candidate in candidates:
            score = self.best_holder_name_score(candidate, holder_names)
            if score > best_score:
                best_candidate = candidate
                best_score = score
        return best_candidate if best_score >= 70 else ""

    def best_holder_name_score(self, candidate: str, holder_names: list[str]) -> float:
        if not candidate.strip():
            return 0.0
        return max((name_similarity(candidate, holder) for holder in holder_names), default=0.0)

    @staticmethod
    def merge_missing_fields(primary: dict, recovered: dict) -> dict:
        merged = primary.copy()
        for key, value in recovered.items():
            if not str(merged.get(key, "")).strip() and str(value).strip():
                merged[key] = str(value).strip()
        return merged
