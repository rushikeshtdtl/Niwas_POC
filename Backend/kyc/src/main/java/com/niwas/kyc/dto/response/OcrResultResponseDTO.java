package com.niwas.kyc.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;

public class OcrResultResponseDTO {

    @JsonProperty("kyc_id")
    private String kycId;

    @JsonProperty("kyc_status")
    private String kycStatus;

    @JsonProperty("identity_score")
    private Integer identityScore;

    @JsonProperty("fraud_score")
    private Integer fraudScore;

    @JsonProperty("risk_score")
    private Integer riskScore;

    @JsonProperty("signature_match_score")
    private Double signatureMatchScore;

    @JsonProperty("final_score")
    private Double finalScore;

    public OcrResultResponseDTO() {
    }

    public String getKycId() {
        return kycId;
    }

    public void setKycId(String kycId) {
        this.kycId = kycId;
    }

    public String getKycStatus() {
        return kycStatus;
    }

    public void setKycStatus(String kycStatus) {
        this.kycStatus = kycStatus;
    }

    public Integer getIdentityScore() {
        return identityScore;
    }

    public void setIdentityScore(Integer identityScore) {
        this.identityScore = identityScore;
    }

    public Integer getFraudScore() {
        return fraudScore;
    }

    public void setFraudScore(Integer fraudScore) {
        this.fraudScore = fraudScore;
    }

    public Integer getRiskScore() {
        return riskScore;
    }

    public void setRiskScore(Integer riskScore) {
        this.riskScore = riskScore;
    }

    public Double getSignatureMatchScore() {
        return signatureMatchScore;
    }

    public void setSignatureMatchScore(Double signatureMatchScore) {
        this.signatureMatchScore = signatureMatchScore;
    }

    public Double getFinalScore() {
        return finalScore;
    }

    public void setFinalScore(Double finalScore) {
        this.finalScore = finalScore;
    }
}
