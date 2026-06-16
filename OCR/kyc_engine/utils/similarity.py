from rapidfuzz import fuzz

from kyc_engine.utils.address_utils import tokenize_address


def name_similarity(left: str, right: str) -> float:
    if not left.strip() or not right.strip():
        return 0.0
    return round(float(fuzz.token_sort_ratio(left, right)), 2)


def address_similarity(left: str, right: str) -> float:
    left_tokens = " ".join(tokenize_address(left))
    right_tokens = " ".join(tokenize_address(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return round(float(fuzz.token_sort_ratio(left_tokens, right_tokens)), 2)
