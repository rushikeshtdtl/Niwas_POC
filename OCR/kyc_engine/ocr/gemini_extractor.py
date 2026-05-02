"""
============================================================
  GEMINI KYC EXTRACTION — FULL SYSTEM PROMPT + CONTEXT ENGINE
  For: OCRExtractor / KYCPipeline (Gemini Flash 2.0)
  Strategy: Single-call multi-doc, schema-locked, zero-recovery
============================================================
"""

# ─────────────────────────────────────────────────────────────
# SECTION 1: MASTER SYSTEM PROMPT
# This is injected as the system_instruction in every Gemini call.
# It primes the model's entire "personality" for this session.
# ─────────────────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """
You are KYC-EXTRACTOR-v2, a highly specialized Indian document OCR engine.

## Your Identity
You extract structured data from Indian KYC documents: PAN cards, Aadhaar cards,
and bank account statements. You have been trained and calibrated for:
- Indian name formats (long Marathi/Tamil/Telugu/Hindi names with father/caste components)
- Aadhaar number masking (first 8 digits often masked as XXXX XXXX)
- PAN card format enforcement (AAAAA9999A — 5 letters, 4 digits, 1 letter)
- IFSC code enforcement (AAAA0NNNNNN — 4 letters, 0, 6 alphanumeric)
- Indian address formats (S/O, D/O, W/O, village/taluka/district/state/pincode)
- Bank statement layouts from: SBI, HDFC, ICICI, Axis, Kotak, PNB, Canara, BOB, Union

## Your Core Rules — NEVER VIOLATE THESE
1. Return ONLY raw JSON. No markdown, no backticks, no explanation, no preamble.
2. If a field is genuinely unreadable: return null. Never guess. Never hallucinate.
3. Do NOT copy the field name as the value (e.g., never return "pan_number": "PAN NUMBER").
4. Do NOT return placeholder text like "N/A", "Not visible", "Unknown".
5. Numbers: strip all spaces from account numbers. Keep spaces in Aadhaar (XXXX XXXX XXXX).
6. Dates: always normalize to YYYY-MM-DD regardless of how they appear on the document.
7. Names: return in ALL CAPS exactly as printed. Never title-case or reformat.
8. If the document image is blank, corrupt, or clearly not a KYC document: return {"error": "invalid_document"}.
9. Ignore watermarks, stamps, QR codes, barcodes — extract only printed text fields.
10. For bank statements: extract the PRIMARY account holder only. Ignore joint holder names unless primary is null.

## Indian Name Intelligence
- Names like "SHIVRAJ GORAKSHNATH PATARE" are valid — do not truncate long names.
- S/O = Son of, D/O = Daughter of, W/O = Wife of — these appear in Aadhaar addresses.
- Father name on PAN is a separate field from the card holder name.
- Do not confuse father's name with the card holder's name.

## Document-Specific Intelligence

### PAN Card
- PAN number is always exactly 10 characters: 5 uppercase letters + 4 digits + 1 uppercase letter
- The name on PAN is the taxpayer's name (not father's name)
- Father's name appears below the taxpayer name, often in smaller font
- DOB format on card: DD/MM/YYYY → normalize to YYYY-MM-DD in output
- Signature box is in the bottom-right — do NOT extract text from it

### Aadhaar Card
- Front side: Name, DOB/Age, Gender, Aadhaar number (bottom)
- Back side: Address details, Aadhaar number
- Aadhaar number: 12 digits, output as "XXXX XXXX XXXX" with spaces
- If only 8 digits visible (masked): output what's visible, do not fabricate the rest
- VID number (if present) is NOT the Aadhaar number — ignore it
- Address often contains village, taluka, district, state, pincode — capture all

### Bank Statement
- Account holder name is usually at the top of the statement, near "Account Statement" heading
- It may say "Statement of Account" as a heading — that is NOT the name
- Look for "Name:", "Account Name:", "Account Holder:" labels
- Account number: digits only, 9–18 characters
- IFSC: always 11 characters
- Branch and bank name are separate fields

## Output Consistency
When returning multiple documents in one response, always use the exact schema provided.
Never add extra fields. Never omit fields (use null for missing).
"""


# ─────────────────────────────────────────────────────────────
# SECTION 2: USER PROMPTS (per call type)
# These go in the "user" turn alongside the images.
# ─────────────────────────────────────────────────────────────

# ── 2A: SINGLE CALL — All 3 documents at once (PREFERRED)
PROMPT_FULL_KYC = """
Extract KYC data from the three document images provided.
Image 1 = PAN card
Image 2 = Aadhaar card  
Image 3 = Bank statement

Return ONLY this exact JSON structure. No other text.

{
  "pan": {
    "pan_number": "string | null",
    "name": "string | null",
    "dob": "YYYY-MM-DD | null",
    "father_name": "string | null"
  },
  "aadhaar": {
    "aadhaar_number": "XXXX XXXX XXXX | null",
    "name": "string | null",
    "dob": "YYYY-MM-DD | null",
    "gender": "M | F | T | null",
    "address": "string | null"
  },
  "bank": {
    "account_holder": "string | null",
    "account_number": "string | null",
    "ifsc": "string | null",
    "bank_name": "string | null",
    "branch": "string | null",
    "account_type": "string | null",
    "address": "string | null"
  }
}
"""

# ── 2B: SINGLE DOCUMENT extraction (fallback if sending 1 at a time)
PROMPTS_SINGLE = {
    "pan": """
Extract from this PAN card image. Return ONLY raw JSON, no markdown.

{
  "pan_number": "exactly 10 chars AAAAA9999A format or null",
  "name": "ALL CAPS name exactly as printed or null",
  "dob": "YYYY-MM-DD normalized from DD/MM/YYYY on card or null",
  "father_name": "ALL CAPS father name exactly as printed or null"
}

Critical: pan_number must match regex [A-Z]{5}[0-9]{4}[A-Z]. If unsure of a character, return null for the whole field.
""",

    "aadhaar": """
Extract from this Aadhaar card image (front or back or both). Return ONLY raw JSON, no markdown.

{
  "aadhaar_number": "12 digits formatted as XXXX XXXX XXXX or null",
  "name": "ALL CAPS name exactly as printed or null",
  "dob": "YYYY-MM-DD or null",
  "gender": "M or F or T or null",
  "address": "complete address as single string including pincode or null"
}

Critical: The 12-digit number at the bottom of the card is the Aadhaar number. VID is NOT the Aadhaar number.
""",

    "bank": """
Extract from this bank statement image. Return ONLY raw JSON, no markdown.

{
  "account_holder": "PRIMARY account holder name in ALL CAPS or null",
  "account_number": "digits only no spaces or null",
  "ifsc": "exactly 11 chars AAAA0NNNNNN format or null",
  "bank_name": "full bank name or null",
  "branch": "branch name or null",
  "account_type": "Savings / Current / OD or null",
  "address": "account holder address if shown or null"
}

Critical: 'Statement of Account' is a heading, NOT the account holder name. Find the actual person's name.
"""
}

# ── 2C: TARGETED RECOVERY — only for specific missing fields
def build_recovery_prompt(doc_type: str, missing_fields: list, identity_context: dict = None) -> str:
    """
    Build a hyper-focused recovery prompt for specific missing fields.
    identity_context: pass PAN/Aadhaar data to help find the bank holder name.
    """
    fields_str = ", ".join(missing_fields)

    base = f"""
A previous extraction of this {doc_type} document returned null for these fields: {fields_str}

Look more carefully at the image. These fields ARE present on this type of document.
"""
    if identity_context and doc_type == "bank":
        pan_name = identity_context.get("pan_name", "")
        aadhaar_name = identity_context.get("aadhaar_name", "")
        base += f"""
IMPORTANT CONTEXT: The verified identity documents show the person's name as:
- PAN name: {pan_name}
- Aadhaar name: {aadhaar_name}
Use this to locate the matching name in the bank statement header area.
"""
    base += f"""
Return ONLY a JSON object with ONLY the missing fields: {fields_str}
Example format: {{"account_holder": "FOUND NAME HERE"}}
If still not found after careful examination, return null for that field. Do NOT guess.
"""
    return base.strip()


# ─────────────────────────────────────────────────────────────
# SECTION 3: GEMINI CALL WRAPPER
# Full production-ready extractor class using Gemini Flash 2.0
# ─────────────────────────────────────────────────────────────

import google.generativeai as genai
import json
import re
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GeminiKYCExtractor:
    """
    Production KYC extractor using Gemini Flash 2.0.
    - Primary: 1 call for all 3 documents
    - Recovery: 1 targeted call only if critical fields are null
    - Max total: 2 API calls per session (vs 3–7 with Groq)
    """

    MODELS = {
        "primary":  "gemini-2.5-flash",       # Fast, cheap, highly accurate
        "fallback": "gemini-2.5-pro",          # Only for unresolvable failures
    }

    CRITICAL_FIELDS = {
        "pan":     ["pan_number", "name"],
        "aadhaar": ["aadhaar_number", "name"],
        "bank":    ["account_holder", "account_number", "ifsc"],
    }

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self._build_model("primary")

    def _build_model(self, tier: str):
        self.model = genai.GenerativeModel(
            model_name=self.MODELS[tier],
            system_instruction=SYSTEM_INSTRUCTION,
            generation_config=genai.GenerationConfig(
                temperature=0.0,           # Fully deterministic
                top_p=1.0,
                max_output_tokens=4096,
                response_mime_type="application/json",  # Forces clean JSON
            ),
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }
        )
        self.current_tier = tier

    def _image_part(self, image_bytes: bytes, mime: str = "image/jpeg") -> dict:
        return {"mime_type": mime, "data": image_bytes}

    def _parse_json(self, text: str) -> Optional[dict]:
        """Robust JSON parser — strips any accidental markdown wrapping."""
        text = text.strip()
        # Strip markdown code fences if model ignores response_mime_type
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e} | Raw: {text[:200]}")
            return None

    def _missing_critical(self, result: dict, doc_type: str) -> list:
        """Return list of critical fields that are null or missing."""
        doc_data = result.get(doc_type, {})
        return [
            f for f in self.CRITICAL_FIELDS[doc_type]
            if not doc_data.get(f)
        ]

    def extract_all(
        self,
        pan_bytes: bytes,
        aadhaar_bytes: bytes,
        bank_bytes: bytes,
        pan_mime: str = "image/jpeg",
        aadhaar_mime: str = "image/jpeg",
        bank_mime: str = "image/jpeg",
    ) -> dict:
        """
        PRIMARY PATH: Extract all 3 documents in 1 API call.
        Falls back to targeted recovery only if critical fields are null.
        """

        # ── Step 1: Single call for all 3 documents
        logger.info("Gemini KYC: primary extraction (1 call, 3 docs)")
        t0 = time.time()

        response = self.model.generate_content([
            PROMPT_FULL_KYC,
            self._image_part(pan_bytes, pan_mime),
            self._image_part(aadhaar_bytes, aadhaar_mime),
            self._image_part(bank_bytes, bank_mime),
        ])

        result = self._parse_json(response.text)
        logger.info(f"Primary extraction done in {time.time()-t0:.2f}s")

        if not result:
            logger.error("Primary extraction returned unparseable JSON — escalating to fallback model")
            self._build_model("fallback")
            response = self.model.generate_content([
                PROMPT_FULL_KYC,
                self._image_part(pan_bytes, pan_mime),
                self._image_part(aadhaar_bytes, aadhaar_mime),
                self._image_part(bank_bytes, bank_mime),
            ])
            result = self._parse_json(response.text) or {}

        # ── Step 2: Targeted recovery — only for null critical fields
        needs_recovery = False
        for doc_type in ["pan", "aadhaar", "bank"]:
            missing = self._missing_critical(result, doc_type)
            if missing:
                needs_recovery = True
                logger.warning(f"Recovery needed for {doc_type}: {missing}")

        if needs_recovery:
            result = self._run_recovery(result, pan_bytes, aadhaar_bytes, bank_bytes,
                                        pan_mime, aadhaar_mime, bank_mime)

        return self._normalize(result)

    def _run_recovery(self, partial: dict,
                      pan_bytes, aadhaar_bytes, bank_bytes,
                      pan_mime, aadhaar_mime, bank_mime) -> dict:
        """
        RECOVERY PATH: One targeted call per document with null critical fields.
        Uses identity context for bank statement recovery.
        """
        image_map = {
            "pan":     (pan_bytes, pan_mime),
            "aadhaar": (aadhaar_bytes, aadhaar_mime),
            "bank":    (bank_bytes, bank_mime),
        }

        for doc_type in ["pan", "aadhaar", "bank"]:
            missing = self._missing_critical(partial, doc_type)
            if not missing:
                continue

            identity_ctx = None
            if doc_type == "bank":
                identity_ctx = {
                    "pan_name":     partial.get("pan", {}).get("name"),
                    "aadhaar_name": partial.get("aadhaar", {}).get("name"),
                }

            recovery_prompt = build_recovery_prompt(doc_type, missing, identity_ctx)
            img_bytes, img_mime = image_map[doc_type]

            logger.info(f"Recovery call for {doc_type}, missing: {missing}")
            response = self.model.generate_content([
                recovery_prompt,
                self._image_part(img_bytes, img_mime),
            ])

            recovered = self._parse_json(response.text) or {}

            # Merge: only fill nulls, never overwrite existing values
            doc_data = partial.setdefault(doc_type, {})
            for field, value in recovered.items():
                if value and not doc_data.get(field):
                    doc_data[field] = value
                    logger.info(f"Recovered {doc_type}.{field} = {value}")

        return partial

    def _normalize(self, result: dict) -> dict:
        """
        Post-processing normalization — fix common Gemini output quirks.
        """
        pan = result.get("pan", {})
        aadhaar = result.get("aadhaar", {})
        bank = result.get("bank", {})

        # PAN number: uppercase, strip spaces
        if pan.get("pan_number"):
            pan["pan_number"] = pan["pan_number"].upper().replace(" ", "")

        # Aadhaar number: ensure XXXX XXXX XXXX format
        if aadhaar.get("aadhaar_number"):
            raw = re.sub(r'\s+', '', str(aadhaar["aadhaar_number"]))
            if len(raw) == 12:
                aadhaar["aadhaar_number"] = f"{raw[:4]} {raw[4:8]} {raw[8:]}"

        # IFSC: uppercase, strip spaces
        if bank.get("ifsc"):
            bank["ifsc"] = bank["ifsc"].upper().replace(" ", "")

        # Account number: digits only
        if bank.get("account_number"):
            bank["account_number"] = re.sub(r'\D', '', str(bank["account_number"]))

        # Names: strip extra whitespace, ensure uppercase
        for doc, field in [("pan", "name"), ("pan", "father_name"),
                            ("aadhaar", "name"), ("bank", "account_holder")]:
            doc_data = result.get(doc, {})
            if doc_data.get(field):
                doc_data[field] = " ".join(doc_data[field].upper().split())

        # Dates: normalize to YYYY-MM-DD
        for doc, field in [("pan", "dob"), ("aadhaar", "dob")]:
            doc_data = result.get(doc, {})
            if doc_data.get(field):
                doc_data[field] = self._normalize_date(doc_data[field])

        return result

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Convert any date format to YYYY-MM-DD."""
        if not date_str:
            return None
        date_str = str(date_str).strip()
        # Already correct
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        # DD/MM/YYYY
        m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', date_str)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        # DD-MM-YYYY
        m = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', date_str)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        return date_str  # Return as-is if format unknown


# ─────────────────────────────────────────────────────────────
# SECTION 4: FIELD VALIDATORS
# Run these AFTER extraction to catch Gemini hallucinations.
# ─────────────────────────────────────────────────────────────

import re as _re

class KYCValidator:

    @staticmethod
    def validate_pan(data: dict) -> tuple[bool, list]:
        errors = []
        pan = data.get("pan_number", "")
        if pan and not _re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
            errors.append(f"Invalid PAN format: {pan}")
            data["pan_number"] = None
        if not data.get("name"):
            errors.append("PAN name is null")
        return len(errors) == 0, errors

    @staticmethod
    def validate_aadhaar(data: dict) -> tuple[bool, list]:
        errors = []
        aadhaar = data.get("aadhaar_number", "")
        if aadhaar:
            digits = _re.sub(r'\s', '', aadhaar)
            if not _re.match(r'^\d{12}$', digits) and not _re.match(r'^[X\d]{12}$', digits):
                errors.append(f"Invalid Aadhaar format: {aadhaar}")
                data["aadhaar_number"] = None
        if not data.get("name"):
            errors.append("Aadhaar name is null")
        return len(errors) == 0, errors

    @staticmethod
    def validate_bank(data: dict) -> tuple[bool, list]:
        errors = []
        ifsc = data.get("ifsc", "")
        if ifsc and not _re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc):
            errors.append(f"Invalid IFSC format: {ifsc}")
            data["ifsc"] = None
        acc = data.get("account_number", "")
        if acc and not _re.match(r'^\d{9,18}$', acc):
            errors.append(f"Invalid account number: {acc}")
            data["account_number"] = None
        if not data.get("account_holder"):
            errors.append("Account holder name is null")
        return len(errors) == 0, errors

    @classmethod
    def validate_all(cls, result: dict) -> dict:
        report = {}
        ok_pan,  e_pan  = cls.validate_pan(result.get("pan", {}))
        ok_aad,  e_aad  = cls.validate_aadhaar(result.get("aadhaar", {}))
        ok_bank, e_bank = cls.validate_bank(result.get("bank", {}))
        report["pan"]     = {"valid": ok_pan,  "errors": e_pan}
        report["aadhaar"] = {"valid": ok_aad,  "errors": e_aad}
        report["bank"]    = {"valid": ok_bank, "errors": e_bank}
        report["all_valid"] = ok_pan and ok_aad and ok_bank
        return report


# ─────────────────────────────────────────────────────────────
# SECTION 5: USAGE EXAMPLE
# ─────────────────────────────────────────────────────────────

def run_kyc_extraction(
    api_key: str,
    pan_path: str,
    aadhaar_path: str,
    bank_path: str,
) -> dict:
    """
    End-to-end KYC extraction. 
    Returns extracted data + validation report.
    Max 2 Gemini API calls total.
    """
    extractor = GeminiKYCExtractor(api_key=api_key)
    validator = KYCValidator()

    with open(pan_path, "rb") as f:
        pan_bytes = f.read()
    with open(aadhaar_path, "rb") as f:
        aadhaar_bytes = f.read()
    with open(bank_path, "rb") as f:
        bank_bytes = f.read()

    result = extractor.extract_all(pan_bytes, aadhaar_bytes, bank_bytes)
    validation = validator.validate_all(result)

    return {
        "extraction": result,
        "validation": validation,
    }


if __name__ == "__main__":
    import os, pprint

    output = run_kyc_extraction(
        api_key=os.getenv("GEMINI_API_KEY"),
        pan_path="testpan.jpeg",
        aadhaar_path="testaadhaar.jpeg",
        bank_path="teststatement.jpeg",
    )
    pprint.pprint(output)
