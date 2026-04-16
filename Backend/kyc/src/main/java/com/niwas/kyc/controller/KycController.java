package com.niwas.kyc.controller;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.niwas.kyc.service.KycService;
import com.niwas.kyc.entity.KycDocument;
import com.niwas.kyc.dto.response.KycResponse;

import java.io.IOException;

@RestController
@RequestMapping("/api/kyc")
public class KycController {

    private final KycService kycService;

    public KycController(KycService kycService) {
        this.kycService = kycService;
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public KycResponse uploadKyc(
            @RequestPart("aadhaar_file") MultipartFile aadhaarFile,
            @RequestPart("pan_file") MultipartFile panFile,
            @RequestPart("bank_statement") MultipartFile bankStatement,
            @RequestPart("signature") MultipartFile signature) throws IOException {

        KycDocument kyc = kycService.uploadKyc(aadhaarFile, panFile, bankStatement, signature);

        return new KycResponse("KYC uploaded successfully", kyc.getKycId(), kyc.getStatus());
    }
}