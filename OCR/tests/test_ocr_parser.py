from kyc_engine.ocr.extractor import OCRExtractor
from kyc_engine.ocr.parser import OCRParser


def test_partial_parser_keeps_only_requested_fields() -> None:
    parser = OCRParser()
    result = parser.parse_partial(
        {"aadhaar_address": ""},
        '{"aadhaar_address":"Vambori Rahuri Ahmednagar Maharashtra 413704","extra":"ignore"}',
    )

    assert result == {"aadhaar_address": "Vambori Rahuri Ahmednagar Maharashtra 413704"}


def test_merge_missing_fields_only_fills_blanks() -> None:
    primary = {
        "statement_name": "MR SHIVRAJ PATARE",
        "statement_account_number": "",
        "statement_ifsc_code": "",
        "statement_address": "",
    }
    recovered = {
        "statement_name": "DO NOT OVERWRITE",
        "statement_account_number": "50100683865085",
        "statement_ifsc_code": "HDFC0000456",
        "statement_address": "Nashik Road",
    }

    merged = OCRExtractor._merge_missing_fields(primary, recovered)

    assert merged["statement_name"] == "MR SHIVRAJ PATARE"
    assert merged["statement_account_number"] == "50100683865085"
    assert merged["statement_ifsc_code"] == "HDFC0000456"
    assert merged["statement_address"] == "Nashik Road"


def test_semantic_merge_prefers_richer_address_and_name_values() -> None:
    extractor = OCRExtractor()
    merged = extractor._semantic_merge_candidates(
        "statement",
        [
            {
                "statement_name": "SHIVRAJ PATARE",
                "statement_account_number": "50100683865085",
                "statement_ifsc_code": "HDFC0000456",
                "statement_address": "Nashik Road",
            },
            {
                "statement_name": "MR SHIVRAJ GORAKSHNATH PATARE",
                "statement_account_number": "50100683865085",
                "statement_ifsc_code": "HDFC0000456",
                "statement_address": "Shop No 3 Mithila Apartments Bytco Point Nashik Road 422101",
            },
        ],
    )

    assert merged["statement_name"] == "MR SHIVRAJ GORAKSHNATH PATARE"
    assert merged["statement_address"] == "Shop No 3 Mithila Apartments Bytco Point Nashik Road 422101"


def test_statement_customer_focus_beats_bank_like_address() -> None:
    extractor = OCRExtractor()
    merged = extractor._semantic_merge_candidates(
        "statement",
        [
            {
                "statement_name": "MR SHIVRAJ GORAKSHNATH PATARE",
                "statement_account_number": "50100683865085",
                "statement_ifsc_code": "HDFC0000456",
                "statement_address": "HDFC Bank Ltd Branch Office Nashik Road IFSC HDFC0000456",
                "_source": "groq",
            },
            {
                "statement_name": "MR SHIVRAJ GORAKSHNATH PATARE",
                "statement_account_number": "50100683865085",
                "statement_ifsc_code": "HDFC0000456",
                "statement_address": "Flat 3 Mithila Apartments Bytco Point Nashik Road 422101",
                "_source": "groq-statement-customer-focus:customer-focus-top-left",
            },
        ],
    )

    assert merged["statement_address"] == "Flat 3 Mithila Apartments Bytco Point Nashik Road 422101"


def test_fallback_multiline_address_extraction() -> None:
    parser = OCRParser()
    text = "\n".join(
        [
            "Address:",
            "S O GORAKSHANATH RAMCHANDRA PATARE",
            "GONDHAL GALLI VAMBORI TAL RAHURI",
            "AHMEDNAGAR MAHARASHTRA 413704",
            "UIDAI",
        ]
    )

    result = parser.parse_fallback("aadhaar", text)

    assert "AHMEDNAGAR" in result["aadhaar_address"].upper()
    assert "413704" in result["aadhaar_address"]


def test_pan_fallback_extracts_name_father_and_dob() -> None:
    parser = OCRParser()
    text = "\n".join(
        [
            "INCOME TAX DEPARTMENT",
            "GOVT OF INDIA",
            "ADITYA GORAKSHNATH PATARE",
            "GORAKSHNATH RAMCHANDRA PATARE",
            "ABCDE1234F",
            "14/04/2003",
        ]
    )

    result = parser.parse_fallback("pan", text)

    assert result["pan_number"] == "ABCDE1234F"
    assert result["pan_name"] == "ADITYA GORAKSHNATH PATARE"
    assert result["pan_father_name"] == "GORAKSHNATH RAMCHANDRA PATARE"
    assert result["pan_dob"] == "14/04/2003"


def test_aadhaar_text_extraction_recovers_name_without_label() -> None:
    parser = OCRParser()
    text = "\n".join(
        [
            "Government of India",
            "ADITYA GORAKSHNATH PATARE",
            "DOB : 14/04/2003",
            "Male",
        ]
    )

    result = parser.parse_text("aadhaar", text)

    assert result["aadhaar_name"] == "ADITYA GORAKSHNATH PATARE"


def test_statement_text_extraction_recovers_customer_name_without_name_label() -> None:
    parser = OCRParser()
    text = "\n".join(
        [
            "HDFC BANK LTD",
            "MR ADITYA GORAKSHNATH PATARE",
            "A/C No 50100683865085",
            "IFSC HDFC0000456",
        ]
    )

    result = parser.parse_text("statement", text)

    assert result["statement_name"] == "MR ADITYA GORAKSHNATH PATARE"
