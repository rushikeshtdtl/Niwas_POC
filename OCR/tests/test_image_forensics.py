from io import BytesIO

from PIL import Image, PngImagePlugin

from kyc_engine.core.file_validator import FilePayload
from kyc_engine.core.fraud import FraudEngine
from kyc_engine.core.image_forensics import ImageForensicsEngine
from kyc_engine.models.schema import ForensicsResult, MatchingResult, ValidationResult


def _png_bytes(with_software: str | None = None) -> bytes:
    image = Image.new("RGB", (500, 300), "white")
    metadata = PngImagePlugin.PngInfo()
    if with_software:
        metadata.add_text("Software", with_software)
    buffer = BytesIO()
    image.save(buffer, format="PNG", pnginfo=metadata)
    return buffer.getvalue()


def test_metadata_audit_flags_editor_software() -> None:
    engine = ImageForensicsEngine()
    payload = FilePayload(
        filename="pan.png",
        content_type="image/png",
        data=_png_bytes("Adobe Photoshop 2024"),
        extension=".png",
        size_bytes=0,
    )
    audit_trail = []

    result = engine._analyze_document("pan", payload, audit_trail)

    assert "metadata_audit" in result.suspicious_layers
    assert any("editor markers=adobe, photoshop" in entry.message.lower() for entry in audit_trail)


def test_forensics_signals_add_fraud_penalty() -> None:
    fraud = FraudEngine()
    validation = ValidationResult(
        pan_validation_status=True,
        aadhaar_validation_status=True,
        statement_validation_status=True,
        signature_validation_status=True,
    )
    matching = MatchingResult(
        pan_to_aadhaar_name_score=95,
        pan_to_statement_name_score=95,
        aadhaar_to_statement_name_score=95,
        aadhaar_to_statement_address_score=90,
        pan_to_aadhaar_dob_match=True,
        signature_match_score=0.9,
    )
    forensics = ForensicsResult(
        documents=[],
        total_suspicious_layers=4,
        high_risk_documents=["pan"],
        fraud_signals=["document_tampering_suspected"],
    )

    result = fraud.evaluate(validation, matching, [], forensics=forensics)

    assert "document_tampering_suspected" in result.fraud_signals
    assert result.fraud_score == 40
