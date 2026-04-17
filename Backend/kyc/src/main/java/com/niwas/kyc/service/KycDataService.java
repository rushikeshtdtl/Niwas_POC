package com.niwas.kyc.service;

import org.springframework.stereotype.Service;
import com.niwas.kyc.entity.KycData;
import com.niwas.kyc.entity.KycDocument;
import com.niwas.kyc.entity.OcrResult;
import com.niwas.kyc.repository.KycDataRepository;
import com.niwas.kyc.repository.KycRepository;
import com.niwas.kyc.repository.OcrResultRepository;
import com.niwas.kyc.dto.response.OcrResultResponseDTO;
import com.niwas.kyc.dto.response.ComplianceKycReportDTO;
import com.niwas.kyc.dto.response.DetailedKycReportDTO;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.Collectors;

@Service
public class KycDataService {

    private final KycDataRepository kycDataRepository;
    private final KycRepository kycRepository;
    private final OcrResultRepository ocrResultRepository;

    public KycDataService(KycDataRepository kycDataRepository, KycRepository kycRepository,
            OcrResultRepository ocrResultRepository) {
        this.kycDataRepository = kycDataRepository;
        this.kycRepository = kycRepository;
        this.ocrResultRepository = ocrResultRepository;
    }

    public Optional<KycData> findByKycId(String kycId) {
        return kycDataRepository.findByKycId(kycId);
    }

    public Optional<OcrResultResponseDTO> getLatestKycDataByUserId(Long userId) {
        // First, get the latest KYC report for the user from kyc_reports table
        Optional<KycDocument> latestKycReport = kycRepository.findLatestByUserId(userId);

        if (latestKycReport.isEmpty()) {
            return Optional.empty();
        }

        // Extract the kyc_id from the latest KYC report
        String kycId = latestKycReport.get().getKycId();

        // Fetch the OCR summary from ocr_results table using the kyc_id
        Optional<OcrResult> ocrResult = ocrResultRepository.findByKycId(kycId);

        return ocrResult.map(this::convertToResponseDTO);
    }

    public KycData save(KycData kycData) {
        return kycDataRepository.save(kycData);
    }

    private OcrResultResponseDTO convertToResponseDTO(OcrResult ocrResult) {
        OcrResultResponseDTO dto = new OcrResultResponseDTO();
        dto.setKycId(ocrResult.getKycId());
        dto.setKycStatus(ocrResult.getKycStatus());
        dto.setIdentityScore(ocrResult.getIdentityScore());
        dto.setFraudScore(ocrResult.getFraudScore());
        dto.setRiskScore(ocrResult.getRiskScore());
        dto.setSignatureMatchScore(ocrResult.getKycScoresSignatureMatchScore());
        dto.setFinalScore(ocrResult.getFinalScore());
        return dto;
    }

    public List<ComplianceKycReportDTO> getAllComplianceReports() {
        List<Object[]> results = kycRepository.findAllComplianceReportsRaw();
        return results.stream()
                .map(row -> new ComplianceKycReportDTO(
                        (String) row[0], // kycId
                        (String) row[1], // status
                        (String) row[2], // date
                        (String) row[3] // userName
                ))
                .collect(Collectors.toList());
    }

    public Optional<DetailedKycReportDTO> getDetailedKycReport(String kycId) {
        // Fetch from kyc_reports table
        Optional<KycDocument> kycDocument = kycRepository.findByKycId(kycId);
        if (kycDocument.isEmpty()) {
            return Optional.empty();
        }

        // Fetch from kyc_data table
        Optional<KycData> kycData = kycDataRepository.findByKycId(kycId);

        // Fetch from ocr_results table
        Optional<OcrResult> ocrResult = ocrResultRepository.findByKycId(kycId);

        // Get user name - we need to query the user table
        // For now, we'll use a placeholder or fetch from existing query
        String userName = getUserNameByKycId(kycId);

        // Build the detailed DTO
        DetailedKycReportDTO dto = new DetailedKycReportDTO();
        dto.setKycId(kycDocument.get().getKycId());
        dto.setStatus(kycDocument.get().getStatus());
        dto.setTimestamp(kycDocument.get().getTimestamp());
        dto.setUserName(userName);

        // Set KYC Data fields
        kycData.ifPresent(data -> {
            dto.setPanNumber(data.getPanNumber());
            dto.setPanName(data.getPanName());
            dto.setPanDob(data.getPanDob());
            dto.setPanFatherName(data.getPanFatherName());
            dto.setPanSignaturePath(data.getPanSignaturePath());
            dto.setAadhaarNumber(data.getAadhaarNumber());
            dto.setAadhaarName(data.getAadhaarName());
            dto.setAadhaarDob(data.getAadhaarDob());
            dto.setAadhaarAddress(data.getAadhaarAddress());
            dto.setStatementName(data.getStatementName());
            dto.setStatementAccountNumber(data.getStatementAccountNumber());
            dto.setStatementIfscCode(data.getStatementIfscCode());
            dto.setStatementAddress(data.getStatementAddress());
            dto.setSignatureLivePath(data.getSignatureLivePath());
        });

        // Set OCR Results fields
        ocrResult.ifPresent(ocr -> {
            dto.setRequestId(ocr.getRequestId());
            dto.setKycStatus(ocr.getKycStatus());
            dto.setIdentityScore(ocr.getIdentityScore());
            dto.setFraudScore(ocr.getFraudScore());
            dto.setRiskScore(ocr.getRiskScore());
            dto.setSignatureMatchScore(ocr.getKycScoresSignatureMatchScore());
            dto.setFinalScore(ocr.getFinalScore());
            dto.setPanToAadhaarNameScore(ocr.getPanToAadhaarNameScore());
            dto.setPanToStatementNameScore(ocr.getPanToStatementNameScore());
            dto.setAadhaarToStatementNameScore(ocr.getAadhaarToStatementNameScore());
            dto.setAadhaarToStatementAddressScore(ocr.getAadhaarToStatementAddressScore());
            dto.setPanToAadhaarDobMatch(ocr.getPanToAadhaarDobMatch());
            dto.setKycMatchingSignatureMatchScore(ocr.getKycMatchingSignatureMatchScore());
            dto.setPanValidationStatus(ocr.getPanValidationStatus());
            dto.setAadhaarValidationStatus(ocr.getAadhaarValidationStatus());
            dto.setStatementValidationStatus(ocr.getStatementValidationStatus());
            dto.setSignatureValidationStatus(ocr.getSignatureValidationStatus());
            dto.setDecisionResult(ocr.getDecisionResult());
            dto.setDecisionReason(ocr.getDecisionReason());
            dto.setOcrLogStatus(ocr.getOcrLogStatus());
            dto.setOcrLogMessage(ocr.getOcrLogMessage());
            dto.setProcessedTimestamp(ocr.getProcessedTimestamp());
        });

        return Optional.of(dto);
    }

    private String getUserNameByKycId(String kycId) {
        // Query to get user name by kyc_id
        // Since kyc_id is unique, we can join kyc_reports with users
        List<Object[]> results = kycRepository.findAllComplianceReportsRaw();
        for (Object[] row : results) {
            if (kycId.equals(row[0])) {
                return (String) row[3]; // userName
            }
        }
        return "Unknown User";
    }
}