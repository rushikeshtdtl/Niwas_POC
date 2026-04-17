package com.niwas.kyc.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "ocr_results")
public class OcrResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "kyc_id", nullable = false)
    private String kycId;

    @Column(name = "request_id")
    private String requestId;

    @Column(name = "kyc_status")
    private String kycStatus;

    @Column(name = "identity_score")
    private Integer identityScore;

    @Column(name = "fraud_score")
    private Integer fraudScore;

    @Column(name = "risk_score")
    private Integer riskScore;

    @Column(name = "kyc_scores_signature_match_score")
    private Double kycScoresSignatureMatchScore;

    @Column(name = "final_score")
    private Double finalScore;

    @Column(name = "pan_to_aadhaar_name_score")
    private Double panToAadhaarNameScore;

    @Column(name = "pan_to_statement_name_score")
    private Double panToStatementNameScore;

    @Column(name = "aadhaar_to_statement_name_score")
    private Double aadhaarToStatementNameScore;

    @Column(name = "aadhaar_to_statement_address_score")
    private Double aadhaarToStatementAddressScore;

    @Column(name = "pan_to_aadhaar_dob_match")
    private Boolean panToAadhaarDobMatch;

    @Column(name = "kyc_matching_signature_match_score")
    private Double kycMatchingSignatureMatchScore;

    @Column(name = "pan_validation_status")
    private Boolean panValidationStatus;

    @Column(name = "aadhaar_validation_status")
    private Boolean aadhaarValidationStatus;

    @Column(name = "statement_validation_status")
    private Boolean statementValidationStatus;

    @Column(name = "signature_validation_status")
    private Boolean signatureValidationStatus;

    @Column(name = "decision_result")
    private String decisionResult;

    @Column(name = "decision_reason")
    private String decisionReason;

    @Column(name = "ocr_log_status")
    private String ocrLogStatus;

    @Column(name = "ocr_log_message")
    private String ocrLogMessage;

    @Column(name = "processed_timestamp")
    private String processedTimestamp;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getKycId() {
        return kycId;
    }

    public void setKycId(String kycId) {
        this.kycId = kycId;
    }

    public String getRequestId() {
        return requestId;
    }

    public void setRequestId(String requestId) {
        this.requestId = requestId;
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

    public Double getKycScoresSignatureMatchScore() {
        return kycScoresSignatureMatchScore;
    }

    public void setKycScoresSignatureMatchScore(Double kycScoresSignatureMatchScore) {
        this.kycScoresSignatureMatchScore = kycScoresSignatureMatchScore;
    }

    public Double getFinalScore() {
        return finalScore;
    }

    public void setFinalScore(Double finalScore) {
        this.finalScore = finalScore;
    }

    public Double getPanToAadhaarNameScore() {
        return panToAadhaarNameScore;
    }

    public void setPanToAadhaarNameScore(Double panToAadhaarNameScore) {
        this.panToAadhaarNameScore = panToAadhaarNameScore;
    }

    public Double getPanToStatementNameScore() {
        return panToStatementNameScore;
    }

    public void setPanToStatementNameScore(Double panToStatementNameScore) {
        this.panToStatementNameScore = panToStatementNameScore;
    }

    public Double getAadhaarToStatementNameScore() {
        return aadhaarToStatementNameScore;
    }

    public void setAadhaarToStatementNameScore(Double aadhaarToStatementNameScore) {
        this.aadhaarToStatementNameScore = aadhaarToStatementNameScore;
    }

    public Double getAadhaarToStatementAddressScore() {
        return aadhaarToStatementAddressScore;
    }

    public void setAadhaarToStatementAddressScore(Double aadhaarToStatementAddressScore) {
        this.aadhaarToStatementAddressScore = aadhaarToStatementAddressScore;
    }

    public Boolean getPanToAadhaarDobMatch() {
        return panToAadhaarDobMatch;
    }

    public void setPanToAadhaarDobMatch(Boolean panToAadhaarDobMatch) {
        this.panToAadhaarDobMatch = panToAadhaarDobMatch;
    }

    public Double getKycMatchingSignatureMatchScore() {
        return kycMatchingSignatureMatchScore;
    }

    public void setKycMatchingSignatureMatchScore(Double kycMatchingSignatureMatchScore) {
        this.kycMatchingSignatureMatchScore = kycMatchingSignatureMatchScore;
    }

    public Boolean getPanValidationStatus() {
        return panValidationStatus;
    }

    public void setPanValidationStatus(Boolean panValidationStatus) {
        this.panValidationStatus = panValidationStatus;
    }

    public Boolean getAadhaarValidationStatus() {
        return aadhaarValidationStatus;
    }

    public void setAadhaarValidationStatus(Boolean aadhaarValidationStatus) {
        this.aadhaarValidationStatus = aadhaarValidationStatus;
    }

    public Boolean getStatementValidationStatus() {
        return statementValidationStatus;
    }

    public void setStatementValidationStatus(Boolean statementValidationStatus) {
        this.statementValidationStatus = statementValidationStatus;
    }

    public Boolean getSignatureValidationStatus() {
        return signatureValidationStatus;
    }

    public void setSignatureValidationStatus(Boolean signatureValidationStatus) {
        this.signatureValidationStatus = signatureValidationStatus;
    }

    public String getDecisionResult() {
        return decisionResult;
    }

    public void setDecisionResult(String decisionResult) {
        this.decisionResult = decisionResult;
    }

    public String getDecisionReason() {
        return decisionReason;
    }

    public void setDecisionReason(String decisionReason) {
        this.decisionReason = decisionReason;
    }

    public String getOcrLogStatus() {
        return ocrLogStatus;
    }

    public void setOcrLogStatus(String ocrLogStatus) {
        this.ocrLogStatus = ocrLogStatus;
    }

    public String getOcrLogMessage() {
        return ocrLogMessage;
    }

    public void setOcrLogMessage(String ocrLogMessage) {
        this.ocrLogMessage = ocrLogMessage;
    }

    public String getProcessedTimestamp() {
        return processedTimestamp;
    }

    public void setProcessedTimestamp(String processedTimestamp) {
        this.processedTimestamp = processedTimestamp;
    }
}
