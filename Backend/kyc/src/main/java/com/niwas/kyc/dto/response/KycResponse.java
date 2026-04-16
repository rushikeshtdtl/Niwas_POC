package com.niwas.kyc.dto.response;

public class KycResponse {

    private String message;
    private String kycId;
    private String status;

    public KycResponse(String message, String kycId, String status) {
        this.message = message;
        this.kycId = kycId;
        this.status = status;
    }

    // Getters and Setters
    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getKycId() {
        return kycId;
    }

    public void setKycId(String kycId) {
        this.kycId = kycId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}