package com.niwas.kyc.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import java.time.LocalDateTime;

@Entity
@Table(name = "kyc_data")
public class KycData {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "kyc_id", nullable = false)
    private String kycId;

    // PAN Details
    @Column(name = "pan_number")
    private String panNumber;

    @Column(name = "pan_name")
    private String panName;

    @Column(name = "pan_dob")
    private String panDob;

    @Column(name = "pan_father_name")
    private String panFatherName;

    @Column(name = "pan_signature_path")
    private String panSignaturePath;

    // Aadhaar Details
    @Column(name = "aadhaar_number")
    private String aadhaarNumber;

    @Column(name = "aadhaar_name")
    private String aadhaarName;

    @Column(name = "aadhaar_dob")
    private String aadhaarDob;

    @Column(name = "aadhaar_address")
    private String aadhaarAddress;

    // Statement Details
    @Column(name = "statement_name")
    private String statementName;

    @Column(name = "statement_account_number")
    private String statementAccountNumber;

    @Column(name = "statement_ifsc_code")
    private String statementIfscCode;

    @Column(name = "statement_address")
    private String statementAddress;

    // Signature Details
    @Column(name = "signature_live_path")
    private String signatureLivePath;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    // Getters and Setters
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

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    // Getters and Setters for PAN Details
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

    // Getters and Setters for Aadhaar Details
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

    // Getters and Setters for Statement Details
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

    // Getters and Setters for Signature Details
    public String getSignatureLivePath() {
        return signatureLivePath;
    }

    public void setSignatureLivePath(String signatureLivePath) {
        this.signatureLivePath = signatureLivePath;
    }
}