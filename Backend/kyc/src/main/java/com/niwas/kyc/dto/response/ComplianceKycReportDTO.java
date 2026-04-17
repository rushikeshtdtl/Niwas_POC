package com.niwas.kyc.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;

public class ComplianceKycReportDTO {

    @JsonProperty("kyc_id")
    private String kycId;

    @JsonProperty("status")
    private String status;

    @JsonProperty("date")
    private String date;

    @JsonProperty("user_name")
    private String userName;

    public ComplianceKycReportDTO() {
    }

    public ComplianceKycReportDTO(String kycId, String status, String date, String userName) {
        this.kycId = kycId;
        this.status = status;
        this.date = date;
        this.userName = userName;
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

    public String getDate() {
        return date;
    }

    public void setDate(String date) {
        this.date = date;
    }

    public String getUserName() {
        return userName;
    }

    public void setUserName(String userName) {
        this.userName = userName;
    }
}
