from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from kyc_engine.models.schema import KYCRequestFiles, KYCResponse
from kyc_engine.pipeline import KYCPipeline
from kyc_engine.utils.audit_logger import persist_audit_record

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.post("/validate", response_model=KYCResponse)
async def validate_kyc(
    pan_file: UploadFile = File(...),
    aadhaar_file: UploadFile = File(...),
    bank_statement: UploadFile = File(...),
    live_signature: UploadFile = File(...),
):
    request_files = KYCRequestFiles(
        pan_file=pan_file,
        aadhaar_file=aadhaar_file,
        bank_statement=bank_statement,
        live_signature=live_signature,
    )
    pipeline = KYCPipeline()
    try:
        response = await pipeline.run(request_files)
        persist_audit_record(response.request_id, response.model_dump())
        return response
    except HTTPException as exc:
        request_id = str(uuid4())
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail)}
        persist_audit_record(
            request_id,
            {
                "request_id": request_id,
                "status": "ERROR",
                "http_status": exc.status_code,
                "detail": detail,
            },
        )
        raise
