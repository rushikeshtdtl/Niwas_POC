package com.niwas.kyc.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;

public class KycResponse {

    private String message;
    private String kycId;
    private String status;

    @JsonProperty("kyc_scores")
    private OcrResponseDTO.KycScores kycScores;

    public KycResponse() {
    }

    public KycResponse(String message, String kycId, String status) {
        this.message = message;
        this.kycId = kycId;
        this.status = status;
    }

    public KycResponse(String message, String kycId, String status, OcrResponseDTO.KycScores kycScores) {
        this.message = message;
        this.kycId = kycId;
        this.status = status;
        this.kycScores = kycScores;
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

    public OcrResponseDTO.KycScores getKycScores() {
        return kycScores;
    }

    public void setKycScores(OcrResponseDTO.KycScores kycScores) {
        this.kycScores = kycScores;
    }
}