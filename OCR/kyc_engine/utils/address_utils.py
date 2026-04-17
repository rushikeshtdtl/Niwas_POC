import re


STOP_WORDS = {
    "india",
    "maharashtra",
    "karnataka",
    "tamil",
    "nadu",
    "gujarat",
    "delhi",
    "state",
}


def normalize_address(address: str) -> str:
    lowered = address.lower().strip()
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def tokenize_address(address: str) -> list[str]:
    return [token for token in normalize_address(address).split() if token and token not in STOP_WORDS]
