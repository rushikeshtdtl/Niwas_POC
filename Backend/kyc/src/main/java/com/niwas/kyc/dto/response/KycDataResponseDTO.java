package com.niwas.kyc.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;

public class KycDataResponseDTO {

    @JsonProperty("kyc_id")
    private String kycId;

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

    public KycDataResponseDTO() {
    }

    // Getters and Setters
    public String getKycId() {
        return kycId;
    }

    public void setKycId(String kycId) {
        this.kycId = kycId;
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
}
