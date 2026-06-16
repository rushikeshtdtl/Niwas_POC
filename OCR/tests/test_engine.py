from io import BytesIO

from fastapi import HTTPException
from PyPDF2 import PdfWriter

from kyc_engine.core.file_validator import FileValidator
from kyc_engine.core.decision import DecisionEngine
from kyc_engine.core.fraud import FraudEngine
from kyc_engine.core.scorer import ScoringEngine
from kyc_engine.core.validator import ValidationEngine
from kyc_engine.models.schema import FraudResult, MatchingResult, ValidationResult


def _matching(
    name1: float,
    name2: float,
    name3: float,
    address: float,
    dob: bool,
    signature: float,
) -> MatchingResult:
    return MatchingResult(
        pan_to_aadhaar_name_score=name1,
        pan_to_statement_name_score=name2,
        aadhaar_to_statement_name_score=name3,
        aadhaar_to_statement_address_score=address,
        pan_to_aadhaar_dob_match=dob,
        signature_match_score=signature,
    )


def test_validation_rejects_invalid_pan() -> None:
    engine = ValidationEngine()
    audit_trail = []
    normalized = {
        "pan_details": {
            "pan_number": "BADPAN",
            "pan_name": "ROHIT SHARMA",
            "pan_dob": "1995-06-15",
            "pan_signature_path": "pan.png",
            "pan_father_name": "MAHESH SHARMA",
        },
        "aadhaar_details": {
            "aadhaar_number": "123412341234",
            "aadhaar_name": "ROHIT SHARMA",
            "aadhaar_dob": "1995-06-15",
            "aadhaar_address": "mumbai india",
        },
        "statement_details": {
            "statement_name": "ROHIT SHARMA",
            "statement_account_number": "1234567890",
            "statement_ifsc_code": "HDFC0001234",
            "statement_address": "mumbai india",
        },
        "signature_details": {"signature_live_path": "live.png"},
    }

    result = engine.validate(normalized, audit_trail)

    assert result.pan_validation_status is False
    assert "Invalid PAN format" in result.validation_errors


def test_perfect_match_scores_approve() -> None:
    audit_trail = []
    matching = _matching(96, 94, 95, 88, True, 0.80)
    validation = ValidationResult(
        pan_validation_status=True,
        aadhaar_validation_status=True,
        statement_validation_status=True,
        signature_validation_status=True,
    )
    fraud = FraudEngine().evaluate(validation, matching, audit_trail)
    scores = ScoringEngine().score(matching, fraud, audit_trail)
    decision = DecisionEngine().decide(scores.final_score, matching, audit_trail)

    assert fraud.fraud_score == 0
    assert scores.identity_score == 100
    assert scores.risk_score == 100
    assert scores.final_score == 100
    assert decision.decision_result == "APPROVE"


def test_major_mismatch_scores_reject() -> None:
    audit_trail = []
    matching = _matching(40, 38, 42, 30, False, 0.20)
    validation = ValidationResult(
        pan_validation_status=True,
        aadhaar_validation_status=True,
        statement_validation_status=True,
        signature_validation_status=True,
    )
    fraud = FraudEngine().evaluate(validation, matching, audit_trail)
    scores = ScoringEngine().score(matching, fraud, audit_trail)
    decision = DecisionEngine().decide(scores.final_score, matching, audit_trail)

    assert fraud.fraud_score == 100
    assert decision.decision_result == "REJECT"


def test_moderate_mismatch_uses_tiered_penalties() -> None:
    audit_trail = []
    matching = _matching(100, 96, 95, 63.95, True, 0.496)
    validation = ValidationResult(
        pan_validation_status=True,
        aadhaar_validation_status=True,
        statement_validation_status=True,
        signature_validation_status=True,
    )

    fraud = FraudEngine().evaluate(validation, matching, audit_trail)
    scores = ScoringEngine().score(matching, fraud, audit_trail)

    assert fraud.fraud_score == 40
    assert fraud.fraud_signals == ["address_mismatch_minor", "signature_mismatch_minor"]
    assert scores.risk_score == 60
    assert scores.final_score == 84


def test_severe_address_mismatch_forces_review() -> None:
    audit_trail = []
    matching = _matching(96, 94, 95, 34.48, True, 0.7886)
    validation = ValidationResult(
        pan_validation_status=True,
        aadhaar_validation_status=True,
        statement_validation_status=True,
        signature_validation_status=True,
    )
    fraud = FraudEngine().evaluate(validation, matching, audit_trail)
    scores = ScoringEngine().score(matching, fraud, audit_trail)
    decision = DecisionEngine().decide(scores.final_score, matching, audit_trail)

    assert scores.final_score == 88
    assert decision.decision_result == "REVIEW"


def test_password_protected_pdf_returns_clean_error() -> None:
    audit_trail = []
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt("secret")
    buffer = BytesIO()
    writer.write(buffer)

    validator = FileValidator()

    try:
        validator._check_corruption(".pdf", buffer.getvalue(), "bank_statement", audit_trail)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail["error"] == "File is password protected"
        assert exc.detail["audit_trail"][-1]["message"] == "bank_statement: File is password protected"
    else:
        raise AssertionError("Expected password-protected PDF to be rejected")


def test_aadhaar_front_side_missing_address_becomes_warning() -> None:
    engine = ValidationEngine()
    audit_trail = []
    normalized = {
        "pan_details": {
            "pan_number": "ABCDE1234F",
            "pan_name": "ROHIT SHARMA",
            "pan_dob": "1995-06-15",
            "pan_signature_path": "pan.png",
            "pan_father_name": "MAHESH SHARMA",
        },
        "aadhaar_details": {
            "aadhaar_number": "123412341234",
            "aadhaar_name": "ROHIT SHARMA",
            "aadhaar_dob": "1995-06-15",
            "aadhaar_address": "",
        },
        "statement_details": {
            "statement_name": "ROHIT SHARMA",
            "statement_account_number": "1234567890",
            "statement_ifsc_code": "HDFC0001234",
            "statement_address": "mumbai india",
        },
        "signature_details": {"signature_live_path": "live.png"},
    }

    result = engine.validate(normalized, audit_trail)

    assert result.aadhaar_validation_status is True
    assert result.validation_errors == []
    assert any("Reupload Aadhaar" in warning for warning in result.validation_warnings)
