from functools import lru_cache
from os import getenv
from pathlib import Path
from shutil import which

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parent.parent


def load_environment() -> None:
    load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)


class Settings(BaseModel):
    gemini_api_key: str = ""
    gemini_vision_model: str = "gemini-1.5-pro"
    tesseract_cmd: str = ""

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def resolved_tesseract_cmd(self) -> str:
        configured = self.tesseract_cmd.strip()
        if configured and Path(configured).exists():
            return configured
        discovered = which("tesseract")
        return discovered or ""

    @property
    def tesseract_available(self) -> bool:
        return bool(self.resolved_tesseract_cmd)

    @property
    def ocr_providers_available(self) -> bool:
        return self.gemini_configured or self.tesseract_available


class RulesConfig(BaseModel):
    identity_weight: float
    fraud_weight: float
    thresholds: dict[str, float]
    penalties: dict[str, int]
    forensics: dict
    ocr: dict


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_environment()
    return Settings(
        gemini_api_key=getenv("GEMINI_API_KEY", "").strip(),
        gemini_vision_model=getenv(
            "GEMINI_VISION_MODEL", "gemini-1.5-pro"
        ).strip(),
        tesseract_cmd=getenv("TESSERACT_CMD", "").strip(),
    )


@lru_cache(maxsize=1)
def get_rules() -> RulesConfig:
    with (ROOT_DIR / "rules.yaml").open("r", encoding="utf-8") as file:
        return RulesConfig.model_validate(yaml.safe_load(file))
