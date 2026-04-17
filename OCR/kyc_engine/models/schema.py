from typing import Literal

from fastapi import UploadFile
from pydantic import BaseModel


class AuditEntry(BaseModel):
    level: Literal["INFO", "WARNING", "ERROR"]
    stage: str
    message: str
    timestamp: str


class OCRLog(BaseModel):
    status: Literal["SUCCESS", "FAILED", "PARTIAL"]
    message: str
    failure_location: str | None = None


class KYCRequestFiles(BaseModel):
    pan_file: UploadFile
    aadhaar_file: UploadFile
    bank_statement: UploadFile
    live_signature: UploadFile

    model_config = {"arbitrary_types_allowed": True}


class PANDetails(BaseModel):
    pan_number: str = ""
    pan_name: str = ""
    pan_dob: str = ""
    pan_father_name: str = ""
    pan_signature_path: str = ""


class AadhaarDetails(BaseModel):
    aadhaar_number: str = ""
    aadhaar_name: str = ""
    aadhaar_dob: str = ""
    aadhaar_address: str = ""


class StatementDetails(BaseModel):
    statement_name: str = ""
    statement_account_number: str = ""
    statement_ifsc_code: str = ""
    statement_address: str = ""


class SignatureDetails(BaseModel):
    signature_live_path: str = ""


class OCRBundle(BaseModel):
    pan_details: PANDetails
    aadhaar_details: AadhaarDetails
    statement_details: StatementDetails
    signature_details: SignatureDetails


class ValidationResult(BaseModel):
    pan_validation_status: bool
    aadhaar_validation_status: bool
    statement_validation_status: bool
    signature_validation_status: bool
    validation_errors: list[str] = []
    validation_warnings: list[str] = []


class MatchingResult(BaseModel):
    pan_to_aadhaar_name_score: float
    pan_to_statement_name_score: float
    aadhaar_to_statement_name_score: float
    aadhaar_to_statement_address_score: float
    pan_to_aadhaar_dob_match: bool
    signature_match_score: float


class FraudBreakdownEntry(BaseModel):
    signal: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    penalty: int
    detail: str


class FraudResult(BaseModel):
    fraud_score: int
    fraud_signals: list[str]
    fraud_breakdown: list[FraudBreakdownEntry] = []


class ForensicLayerResult(BaseModel):
    layer_name: str
    suspicious: bool
    score: float
    detail: str


class DocumentForensicsResult(BaseModel):
    document_type: str
    overall_score: int
    suspicious_layers: list[str]
    layers: list[ForensicLayerResult]


class ForensicsResult(BaseModel):
    documents: list[DocumentForensicsResult]
    total_suspicious_layers: int
    high_risk_documents: list[str]
    fraud_signals: list[str]


class ScoreResult(BaseModel):
    identity_score: int
    fraud_score: int
    risk_score: int
    signature_match_score: float
    final_score: float


class DecisionResult(BaseModel):
    decision_result: Literal["APPROVE", "REVIEW", "REJECT"]
    decision_reason: str


class KYCResponse(BaseModel):
    request_id: str
    kyc_status: Literal["APPROVE", "REVIEW", "REJECT"]
    kyc_scores: ScoreResult
    kyc_matching: MatchingResult
    kyc_validation: ValidationResult
    kyc_fraud: FraudResult
    kyc_forensics: ForensicsResult
    kyc_decision: DecisionResult
    ocr_data: OCRBundle
    ocr_log: OCRLog
    audit_trail: list[AuditEntry]
    processed_timestamp: str
