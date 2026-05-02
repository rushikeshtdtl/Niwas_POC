import json
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT_DIR / "logs"


def persist_audit_record(request_id: str, payload: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = LOG_DIR / f"kyc_{timestamp}_{request_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
