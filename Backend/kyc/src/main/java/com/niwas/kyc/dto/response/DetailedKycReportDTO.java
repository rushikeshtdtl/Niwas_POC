package com.niwas.kyc.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;

public class DetailedKycReportDTO {

    // Basic KYC Report Info
    @JsonProperty("kyc_id")
    private String kycId;

    @JsonProperty("status")
    private String status;

    @JsonProperty("timestamp")
    private LocalDateTime timestamp;

    @JsonProperty("user_name")
    private String userName;

    // KYC Data Fields
    @JsonProperty("pan_number")
    private String panNumber;

    @JsonProperty("pan_name")
    private String panName;

    @JsonProperty("pan_dob")
    private String panDob;

    @JsonProperty("pan_father_name")
    private String panFatherName;

    @JsonProperty("pan_signature_path")
    private String panSignaturePath;

    @JsonProperty("aadhaar_number")
    private String aadhaarNumber;

    @JsonProperty("aadhaar_name")
    private String aadhaarName;

    @JsonProperty("aadhaar_dob")
    private String aadhaarDob;

    @JsonProperty("aadhaar_address")
    private String aadhaarAddress;

    @JsonProperty("statement_name")
    private String statementName;

    @JsonProperty("statement_account_number")
    private String statementAccountNumber;

    @JsonProperty("statement_ifsc_code")
    private String statementIfscCode;

    @JsonProperty("statement_address")
    private String statementAddress;

    @JsonProperty("signature_live_path")
    private String signatureLivePath;

    // OCR Results Fields
    @JsonProperty("request_id")
    private String requestId;

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

    @JsonProperty("pan_to_aadhaar_name_score")
    private Double panToAadhaarNameScore;

    @JsonProperty("pan_to_statement_name_score")
    private Double panToStatementNameScore;

    @JsonProperty("aadhaar_to_statement_name_score")
    private Double aadhaarToStatementNameScore;

    @JsonProperty("aadhaar_to_statement_address_score")
    private Double aadhaarToStatementAddressScore;

    @JsonProperty("pan_to_aadhaar_dob_match")
    private Boolean panToAadhaarDobMatch;

    @JsonProperty("kyc_matching_signature_match_score")
    private Double kycMatchingSignatureMatchScore;

    @JsonProperty("pan_validation_status")
    private Boolean panValidationStatus;

    @JsonProperty("aadhaar_validation_status")
    private Boolean aadhaarValidationStatus;

    @JsonProperty("statement_validation_status")
    private Boolean statementValidationStatus;

    @JsonProperty("signature_validation_status")
    private Boolean signatureValidationStatus;

    @JsonProperty("decision_result")
    private String decisionResult;

    @JsonProperty("decision_reason")
    private String decisionReason;

    @JsonProperty("ocr_log_status")
    private String ocrLogStatus;

    @JsonProperty("ocr_log_message")
    private String ocrLogMessage;

    @JsonProperty("processed_timestamp")
    private String processedTimestamp;

    // Default constructor
    public DetailedKycReportDTO() {
    }

    // Getters and Setters
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

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }

    public String getUserName() {
        return userName;
    }

    public void setUserName(String userName) {
        this.userName = userName;
    }

    public String getPanNumber() {
        return panNumber;
    }

    public void setPanNumber(String panNumber) {
        this.panNumber = panNumber;
    }

    public String getPanName() {
        return panName;
    }

    public void setPanName(String panName) {
        this.panName = panName;
    }

    public String getPanDob() {
        return panDob;
    }

    public void setPanDob(String panDob) {
        this.panDob = panDob;
    }

    public String getPanFatherName() {
        return panFatherName;
    }

    public void setPanFatherName(String panFatherName) {
        this.panFatherName = panFatherName;
    }

    public String getPanSignaturePath() {
        return panSignaturePath;
    }

    public void setPanSignaturePath(String panSignaturePath) {
        this.panSignaturePath = panSignaturePath;
    }

    public String getAadhaarNumber() {
        return aadhaarNumber;
    }

    public void setAadhaarNumber(String aadhaarNumber) {
        this.aadhaarNumber = aadhaarNumber;
    }

    public String getAadhaarName() {
        return aadhaarName;
    }

    public void setAadhaarName(String aadhaarName) {
        this.aadhaarName = aadhaarName;
    }

    public String getAadhaarDob() {
        return aadhaarDob;
    }

    public void setAadhaarDob(String aadhaarDob) {
        this.aadhaarDob = aadhaarDob;
    }

    public String getAadhaarAddress() {
        return aadhaarAddress;
    }

    public void setAadhaarAddress(String aadhaarAddress) {
        this.aadhaarAddress = aadhaarAddress;
    }

    public String getStatementName() {
        return statementName;
    }

    public void setStatementName(String statementName) {
        this.statementName = statementName;
    }

    public String getStatementAccountNumber() {
        return statementAccountNumber;
    }

    public void setStatementAccountNumber(String statementAccountNumber) {
        this.statementAccountNumber = statementAccountNumber;
    }

    public String getStatementIfscCode() {
        return statementIfscCode;
    }

    public void setStatementIfscCode(String statementIfscCode) {
        this.statementIfscCode = statementIfscCode;
    }

    public String getStatementAddress() {
        return statementAddress;
    }

    public void setStatementAddress(String statementAddress) {
        this.statementAddress = statementAddress;
    }

    public String getSignatureLivePath() {
        return signatureLivePath;
    }

    public void setSignatureLivePath(String signatureLivePath) {
        this.signatureLivePath = signatureLivePath;
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