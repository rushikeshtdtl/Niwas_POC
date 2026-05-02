# OCR Module

The OCR module is a Zero-Trust Deterministic KYC Validation Engine designed to process and validate identity documents with a full audit trail. It handles extraction and verification for PAN cards, Aadhaar cards, bank statements, and live signatures.

## Features

- **Document Extraction**: Automated extraction of data from PAN and Aadhaar cards.
- **Verification**: Deterministic rule-based matching and validation of extracted data.
- **Forensics**: Integrated forensic checks and fraud scoring.
- **Hybrid OCR**: Utilizes Gemini 1.5 Pro (AI-powered) when an API key is provided, with local fallback options.
- **Audit Trail**: Every request generates a detailed JSON audit record for compliance and debugging.
- **Partial Validation**: Returns extracted fields plus validation warnings instead of hard-failing for incomplete documents.
- **Aadhaar Intelligence**: Detects front-side-only Aadhaar images and guides users to upload complete documents.

## Setup Instructions

1.  **Prerequisites**:
    - Python 3.9+
    - Tesseract OCR engine (installed and added to PATH)

2.  **Installation**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**:
    - Copy `.env.example` to `.env`
    - Configure the following variables:
        - `GEMINI_API_KEY` (Required: for AI-enhanced OCR)
        - `GEMINI_VISION_MODEL` (Defaults to `gemini-1.5-pro`)
        - `TESSERACT_CMD` (Optional: path to tesseract executable if not in PATH)

## Running the OCR Service

To start the FastAPI server:

```bash
python -m uvicorn kyc_engine.main:app --reload
```

The service will be available at `http://127.0.0.1:8000`.
You can access the interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.

## Endpoint Overview

- **POST /kyc/validate**: Validates KYC documents.
    - Expects multipart form data:
        - `pan_file`: PAN card image.
        - `aadhaar_file`: Aadhaar card image/PDF.
        - `bank_statement`: Bank statement document.
        - `live_signature`: Image of the live signature.
