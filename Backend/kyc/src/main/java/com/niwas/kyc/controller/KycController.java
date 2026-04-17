package com.niwas.kyc.controller;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.niwas.kyc.service.KycService;
import com.niwas.kyc.service.KycDataService;
import com.niwas.kyc.dto.response.KycResponse;
import com.niwas.kyc.dto.response.OcrResponseDTO;
import com.niwas.kyc.dto.response.OcrResultResponseDTO;
import com.niwas.kyc.model.User;
import com.niwas.kyc.repository.UserRepository;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.Authentication;

import java.io.IOException;
import java.util.Optional;

@RestController
@RequestMapping("/api/kyc")
public class KycController {

    private final KycService kycService;
    private final KycDataService kycDataService;
    private final UserRepository userRepository;

    public KycController(KycService kycService, KycDataService kycDataService, UserRepository userRepository) {
        this.kycService = kycService;
        this.kycDataService = kycDataService;
        this.userRepository = userRepository;
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public KycResponse uploadKyc(
            @RequestPart("aadhaar_file") MultipartFile aadhaarFile,
            @RequestPart("pan_file") MultipartFile panFile,
            @RequestPart("bank_statement") MultipartFile bankStatement,
            @RequestPart("signature") MultipartFile signature) throws IOException {

        OcrResponseDTO ocrResponse = kycService.uploadKyc(aadhaarFile, panFile, bankStatement, signature);

        return new KycResponse("KYC uploaded successfully", ocrResponse.getKycId(), ocrResponse.getKycStatus(),
                ocrResponse.getKycScores());
    }

    @GetMapping("/data")
    public OcrResultResponseDTO getLatestKycData() {
        // Get authenticated user
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        String mobile = (String) auth.getPrincipal();
        User user = userRepository.findByPhone(mobile)
                .orElseThrow(() -> new RuntimeException("User not found"));

        // Get latest OCR result for the user's latest KYC report
        Optional<OcrResultResponseDTO> ocrResult = kycDataService.getLatestKycDataByUserId(user.getUserId());

        if (ocrResult.isEmpty()) {
            throw new RuntimeException("No KYC data found for user");
        }

        return ocrResult.get();
    }
}