package com.niwas.kyc.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.niwas.kyc.service.KycDataService;
import com.niwas.kyc.dto.response.ComplianceKycReportDTO;
import com.niwas.kyc.dto.response.DetailedKycReportDTO;
import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/compliance")
public class ComplianceController {

    private final KycDataService kycDataService;

    public ComplianceController(KycDataService kycDataService) {
        this.kycDataService = kycDataService;
    }

    @GetMapping("/kyc-reports")
    public ResponseEntity<List<ComplianceKycReportDTO>> getAllKycReports() {
        List<ComplianceKycReportDTO> reports = kycDataService.getAllComplianceReports();
        return ResponseEntity.ok(reports);
    }

    @GetMapping("/kyc-reports/{kycId}")
    public ResponseEntity<DetailedKycReportDTO> getDetailedKycReport(@PathVariable String kycId) {
        Optional<DetailedKycReportDTO> report = kycDataService.getDetailedKycReport(kycId);
        return report.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
