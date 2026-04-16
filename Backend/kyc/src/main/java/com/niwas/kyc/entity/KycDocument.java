package com.niwas.kyc.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "kyc_reports")
public class KycDocument {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "kyc_id", unique = true, nullable = false)
    private String kycId;

    @Column(name = "status", nullable = false)
    private String status = "in_process";

    @Column(name = "aadhaar_file")
    private String aadhaarFile;

    @Column(name = "pan_file")
    private String panFile;

    @Column(name = "bank_statement")
    private String bankStatement;

    @Column(name = "signature")
    private String signature;

    @Column(name = "timestamp", nullable = false)
    private LocalDateTime timestamp = LocalDateTime.now();

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

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getAadhaarFile() {
        return aadhaarFile;
    }

    public void setAadhaarFile(String aadhaarFile) {
        this.aadhaarFile = aadhaarFile;
    }

    public String getPanFile() {
        return panFile;
    }

    public void setPanFile(String panFile) {
        this.panFile = panFile;
    }

    public String getBankStatement() {
        return bankStatement;
    }

    public void setBankStatement(String bankStatement) {
        this.bankStatement = bankStatement;
    }

    public String getSignature() {
        return signature;
    }

    public void setSignature(String signature) {
        this.signature = signature;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }
}