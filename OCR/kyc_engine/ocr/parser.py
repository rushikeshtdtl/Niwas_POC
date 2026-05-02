import json
import re


class OCRParser:
    def build_prompt(self, document_type: str) -> str:
        schemas = {
            "pan": (
                '{"pan_number":"","pan_name":"","pan_dob":"","pan_father_name":"","pan_signature_path":""}'
            ),
            "aadhaar": '{"aadhaar_number":"","aadhaar_name":"","aadhaar_dob":"","aadhaar_address":""}',
            "statement": (
                '{"statement_name":"","statement_account_number":"","statement_ifsc_code":"","statement_address":""}'
            ),
            "signature": '{"signature_live_path":""}',
        }
        extra = {
            "pan": "Capture visible PAN holder name, PAN number, DOB, father name, and signature path if available.",
            "aadhaar": (
                "Capture the full Aadhaar postal address exactly as visible, including house, street, locality, city, state, and pincode when present. "
                "If the image appears to show both sides, extract address from the address side. If only the front side is visible, keep aadhaar_address empty."
            ),
            "statement": (
                "Capture account holder name, account number, IFSC code, and full communication address exactly as visible. "
                "Prefer the customer/account-holder block and ignore branch, footer, and contact-center details."
            ),
            "signature": "Capture only the signature image path if available.",
        }
        return (
            f"Extract the document as JSON using this exact schema and exact prefixed keys only: {schemas[document_type]}. "
            "Return empty strings when a value is not visible. Do not invent values. "
            f"{extra[document_type]}"
        )

    def build_focus_prompt(self, document_type: str, fields: list[str]) -> str:
        schemas = {
            "pan": '{"pan_number":"","pan_name":"","pan_dob":"","pan_father_name":""}',
            "aadhaar": '{"aadhaar_name":"","aadhaar_address":""}',
            "statement": (
                '{"statement_name":"","statement_account_number":"","statement_ifsc_code":"","statement_address":""}'
            ),
        }
        instructions = {
            "pan_number": "Read the PAN number exactly as visible.",
            "pan_name": "Read the PAN holder name exactly as visible.",
            "pan_dob": "Read the PAN date of birth exactly as visible.",
            "pan_father_name": "Read the PAN father name exactly as visible.",
            "aadhaar_name": "Read the Aadhaar holder name exactly as visible.",
            "aadhaar_address": (
                "Read only the Aadhaar address block and return the full postal address exactly as visible. "
                "Do not shorten or summarize the address."
            ),
            "statement_name": "Read the bank statement account holder/customer name exactly as visible.",
            "statement_account_number": "Read the bank account number exactly as visible.",
            "statement_ifsc_code": "Read the IFSC code exactly as visible.",
            "statement_address": (
                "Read only the customer/account-holder communication address exactly as visible. "
                "Ignore branch address, bank office address, footer address, and customer-care/contact blocks. "
                "Prefer the address block immediately below or beside the account-holder name."
            ),
        }
        field_instructions = " ".join(
            instructions[field] for field in fields if field in instructions
        )
        return (
            f"Extract only these fields {fields} as valid JSON using this schema: {schemas[document_type]}. "
            "Return empty strings when a value is not visible. Do not invent values. "
            f"{field_instructions}"
        )

    def parse(self, document_type: str, raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return self.empty_document(document_type)
            data = json.loads(match.group(0))

        expected = self.empty_document(document_type)
        expected.update({key: str(data.get(key, "") or "") for key in expected})
        return expected

    def parse_partial(self, schema: dict[str, str], raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return schema.copy()
            data = json.loads(match.group(0))

        merged = schema.copy()
        merged.update({key: str(data.get(key, "") or "") for key in schema})
        return merged

    def parse_fallback(self, document_type: str, text: str) -> dict:
        if document_type == "pan":
            pan_name, pan_father_name = self._extract_pan_name_and_father(text)
            return {
                "pan_number": self._extract_pan_number(text),
                "pan_name": pan_name,
                "pan_dob": self._extract_pan_dob(text),
                "pan_father_name": pan_father_name,
                "pan_signature_path": "",
            }
        if document_type == "aadhaar":
            return {
                "aadhaar_number": self._find(text, r"\b(\d{4}\s?\d{4}\s?\d{4})\b"),
                "aadhaar_name": self._extract_aadhaar_name(text),
                "aadhaar_dob": self._find(text, r"\b(\d{2}[/-]\d{2}[/-]\d{4}|\d{4})\b"),
                "aadhaar_address": self._extract_aadhaar_address(text),
            }
        if document_type == "statement":
            return {
                "statement_name": self._extract_statement_name(text),
                "statement_account_number": self._find(
                    text, r"(?:Account Number|A/C No\.?|Account No\.?)[:\s-]*([A-Z0-9-]+)", flags=re.IGNORECASE
                ),
                "statement_ifsc_code": self._extract_statement_ifsc(text),
                "statement_address": self._extract_statement_address(text),
            }
        return self.empty_document(document_type)

    def empty_document(self, document_type: str) -> dict:
        templates = {
            "pan": {
                "pan_number": "",
                "pan_name": "",
                "pan_dob": "",
                "pan_father_name": "",
                "pan_signature_path": "",
            },
            "aadhaar": {
                "aadhaar_number": "",
                "aadhaar_name": "",
                "aadhaar_dob": "",
                "aadhaar_address": "",
            },
            "statement": {
                "statement_name": "",
                "statement_account_number": "",
                "statement_ifsc_code": "",
                "statement_address": "",
            },
            "signature": {
                "signature_live_path": "",
            },
        }
        return templates[document_type].copy()

    @staticmethod
    def _find(text: str, pattern: str, flags: int = 0) -> str:
        match = re.search(pattern, text, flags)
        if not match:
            return ""
        return match.group(1).strip()

    @staticmethod
    def _extract_multiline_block(
        text: str, markers: list[str], stop_markers: list[str]
    ) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        capturing = False
        captured: list[str] = []
        for line in lines:
            lower_line = line.lower()
            if any(marker in lower_line for marker in markers):
                capturing = True
                cleaned = re.sub(
                    r"^(address|communication address|customer address)[:\s-]*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip()
                if cleaned:
                    captured.append(cleaned)
                continue
            if capturing and any(stop in lower_line for stop in stop_markers):
                break
            if capturing:
                captured.append(line)
                if len(captured) >= 5:
                    break
        return " ".join(captured).strip()

    def parse_text(self, document_type: str, raw_text: str) -> dict:
        if not raw_text or not raw_text.strip():
            return self.empty_document(document_type)

        if document_type == "pan":
            pan_name, pan_father_name = self._extract_pan_name_and_father(raw_text)
            return {
                "pan_number": self._extract_pan_number(raw_text),
                "pan_name": pan_name,
                "pan_dob": self._extract_pan_dob(raw_text),
                "pan_father_name": pan_father_name,
                "pan_signature_path": "",
            }
        if document_type == "aadhaar":
            return {
                "aadhaar_number": self._find(raw_text, r"\b(\d{4}\s?\d{4}\s?\d{4})\b"),
                "aadhaar_name": self._extract_aadhaar_name(raw_text),
                "aadhaar_dob": self._find(
                    raw_text, r"\b(\d{2}[/-]\d{2}[/-]\d{4}|\d{4})\b"
                ),
                "aadhaar_address": self._extract_aadhaar_address(raw_text),
            }
        if document_type == "statement":
            return {
                "statement_name": self._extract_statement_name(raw_text),
                "statement_account_number": self._find(
                    raw_text, r"(?:Account Number|A/C No\.?|Account No\.?)[:\s-]*([A-Z0-9-]+)", flags=re.IGNORECASE
                ),
                "statement_ifsc_code": self._extract_statement_ifsc(raw_text),
                "statement_address": self._extract_statement_address(raw_text),
            }
        return self.empty_document(document_type)

    def _extract_aadhaar_address(self, text: str) -> str:
        address = self._extract_multiline_block(
            text,
            ["address", "addres", "addr"],
            stop_markers=["uidai", "vid", "mobile", "help"],
        )
        if address:
            return address

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        pincode_index = -1
        for index, line in enumerate(lines):
            if re.search(r"\b\d{6}\b", line):
                pincode_index = index
                break
        if pincode_index == -1:
            return ""

        start = max(0, pincode_index - 3)
        block = " ".join(lines[start : pincode_index + 1]).strip()
        if len(block.split()) >= 5:
            return block
        return ""

    def _extract_aadhaar_name(self, text: str) -> str:
        labeled = self._find(
            text,
            r"(?:NAME|नाम)[:\s-]*([A-Z][A-Z ]{3,})",
            flags=re.IGNORECASE,
        )
        if labeled:
            return labeled

        ignored_markers = {
            "government",
            "india",
            "uidai",
            "address",
            "dob",
            "yob",
            "male",
            "female",
            "maharashtra",
        }
        candidates: list[str] = []
        for raw_line in text.splitlines():
            line = re.sub(r"[^A-Z ]", " ", raw_line.upper()).strip()
            line = re.sub(r"\s+", " ", line)
            if len(line.split()) < 2:
                continue
            lowered = line.lower()
            if any(marker in lowered for marker in ignored_markers):
                continue
            if re.search(r"\d", line):
                continue
            if len(line) < 8 or len(line) > 40:
                continue
            candidates.append(line)

        for candidate in candidates:
            if 2 <= len(candidate.split()) <= 4:
                return candidate
        return candidates[0] if candidates else ""

    def _extract_pan_number(self, text: str) -> str:
        return self._find(text.upper(), r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")

    def _extract_pan_dob(self, text: str) -> str:
        labeled = self._find(
            text,
            r"(?:DATE OF BIRTH|DOB|BIRTH)[:\s-]*(\d{2}[/-]\d{2}[/-]\d{4})",
            flags=re.IGNORECASE,
        )
        if labeled:
            return labeled
        return self._find(text, r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b")

    def _extract_pan_name_and_father(self, text: str) -> tuple[str, str]:
        labeled_name = self._find(
            text,
            r"(?:NAME)[:\s-]*([A-Z][A-Z ]{3,})",
            flags=re.IGNORECASE,
        )
        labeled_father = self._find(
            text,
            r"(?:FATHER'?S NAME)[:\s-]*([A-Z][A-Z ]{3,})",
            flags=re.IGNORECASE,
        )
        if labeled_name or labeled_father:
            return labeled_name, labeled_father

        ignored_tokens = {
            "INCOME",
            "TAX",
            "DEPARTMENT",
            "PERMANENT",
            "ACCOUNT",
            "NUMBER",
            "CARD",
            "SIGNATURE",
            "GOVT",
            "INDIA",
            "GOVERNMENT",
            "DATE",
            "BIRTH",
            "DOB",
        }
        candidates: list[str] = []
        for raw_line in text.splitlines():
            line = re.sub(r"[^A-Z ]", " ", raw_line.upper()).strip()
            line = re.sub(r"\s+", " ", line)
            if len(line.split()) < 2:
                continue
            if any(token in ignored_tokens for token in line.split()):
                continue
            if len(line) < 6:
                continue
            candidates.append(line)

        deduped: list[str] = []
        for candidate in candidates:
            if candidate not in deduped:
                deduped.append(candidate)

        name = deduped[0] if deduped else ""
        father = deduped[1] if len(deduped) > 1 else ""
        return name, father

    def _extract_statement_ifsc(self, text: str) -> str:
        labeled = self._find(
            text,
            r"(?:IFSC(?:\s*Code)?|IFS Code)[:\s-]*([A-Z]{4}0[A-Z0-9]{6})",
            flags=re.IGNORECASE,
        )
        if labeled:
            return labeled
        return self._find(text, r"\b([A-Z]{4}0[A-Z0-9]{6})\b")

    def _extract_statement_name(self, text: str) -> str:
        labeled = self._find(
            text,
            r"(?:Account Name|Customer Name|Name|A/C Name)[:\s-]*(.+)",
            flags=re.IGNORECASE,
        )
        if labeled:
            return labeled.strip()

        ignored_markers = {
            "bank",
            "statement",
            "branch",
            "ifsc",
            "micr",
            "address",
            "account",
            "email",
            "phone",
            "customer care",
            "date",
            "balance",
        }
        candidates: list[str] = []
        for raw_line in text.splitlines():
            line = re.sub(r"\s+", " ", raw_line.strip())
            if not line:
                continue
            lowered = line.lower()
            if any(marker in lowered for marker in ignored_markers):
                continue
            if re.search(r"\d{4,}", line):
                continue
            if len(line.split()) < 2:
                continue
            if len(line) < 6 or len(line) > 60:
                continue
            candidates.append(line)

        for candidate in candidates:
            normalized = re.sub(r"[^A-Z ]", " ", candidate.upper())
            normalized = re.sub(r"\s+", " ", normalized).strip()
            if 2 <= len(normalized.split()) <= 6:
                return normalized
        return ""

    def _extract_statement_address(self, text: str) -> str:
        address = self._extract_multiline_block(
            text,
            ["communication address", "customer address", "address for communication", "mailing address", "address"],
            stop_markers=["ifsc", "account", "branch", "statement", "email", "phone"],
        )
        if address:
            return address

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        candidate_lines = [
            line
            for line in lines
            if re.search(r"\b\d{6}\b", line) or any(
                token in line.lower()
                for token in ["road", "street", "nagar", "society", "flat", "apt", "apartment", "plot", "tal", "dist"]
            )
        ]
        if not candidate_lines:
            return ""

        return " ".join(candidate_lines[:4]).strip()
