package com.niwas.kyc.service;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import com.niwas.kyc.entity.KycDocument;
import com.niwas.kyc.repository.KycRepository;
import com.niwas.kyc.repository.UserRepository;
import com.niwas.kyc.model.User;
import com.niwas.kyc.client.OcrClient;
import com.niwas.kyc.dto.response.OcrResponseDTO;
import com.niwas.kyc.util.FuzzyMatcher;
import com.niwas.kyc.repository.KycDataRepository;
import com.niwas.kyc.entity.KycData;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.Authentication;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;
import java.util.Arrays;
import java.util.List;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.io.RandomAccessReadBuffer;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.encryption.InvalidPasswordException;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;

@Service
public class KycService {

    private final KycRepository kycRepository;
    private final UserRepository userRepository;
    private final KycDataRepository kycDataRepository;
    private final OcrClient ocrClient;
    private final FuzzyMatcher fuzzyMatcher;

    private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(KycService.class);
    private static final String UPLOAD_DIR = "uploads/kyc/";

    public KycService(KycRepository kycRepository, UserRepository userRepository, 
            KycDataRepository kycDataRepository, OcrClient ocrClient, FuzzyMatcher fuzzyMatcher) {
        this.kycRepository = kycRepository;
        this.userRepository = userRepository;
        this.kycDataRepository = kycDataRepository;
        this.ocrClient = ocrClient;
        this.fuzzyMatcher = fuzzyMatcher;
    }

    public OcrResponseDTO uploadKyc(MultipartFile aadhaarFile, MultipartFile panFile, MultipartFile bankStatement,
            MultipartFile signature) throws IOException {
        logger.info("=== KycService: uploadKyc method entered ===");
        
        // Get authenticated user
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null) {
            logger.error("Authentication object is null in SecurityContext");
            throw new RuntimeException("Authentication not found!");
        }
        
        String mobile = auth.getPrincipal().toString();
        String loginName = (auth.getDetails() != null) ? auth.getDetails().toString() : null;
        
        logger.info("Service process for mobile: {}", mobile);
        logger.info("Session Login Name: {}", loginName);
        
        User user = userRepository.findByPhone(mobile).orElseThrow(() -> {
            logger.error("User not found in DB for phone: {}", mobile);
            return new RuntimeException("User not found for mobile: " + mobile);
        });
        logger.info("Database User match: {}", user.getName());

        // Validate files presence
        if (aadhaarFile.isEmpty() || panFile.isEmpty() || bankStatement.isEmpty() || signature.isEmpty()) {
            throw new RuntimeException("All documents are required");
        }

        // Validate file types and readability
        validateFile(aadhaarFile, Arrays.asList("jpg", "jpeg", "png", "pdf"));
        validateFile(panFile, Arrays.asList("jpg", "jpeg", "png", "pdf"));
        validateFile(bankStatement, Arrays.asList("pdf"));
        validateFile(signature, Arrays.asList("jpg", "jpeg", "png", "pdf"));

        // Generate unique kyc_id
        String generatedKycId;
        do {
            generatedKycId = "KYC" + java.time.Year.now().getValue() + generateRandomString(6);
        } while (kycRepository.existsByKycId(generatedKycId));
        final String kycId = generatedKycId;

        // Create directory
        Path kycDir = Paths.get(UPLOAD_DIR + kycId);
        Files.createDirectories(kycDir);

        // Save files
        String aadhaarPath = saveFile(aadhaarFile, kycDir, "aadhaar");
        String panPath = saveFile(panFile, kycDir, "pan");
        String bankPath = saveFile(bankStatement, kycDir, "bank_statement");
        String signaturePath = saveFile(signature, kycDir, "signature");

        // Save to DB
        KycDocument kyc = new KycDocument();
        kyc.setUserId(user.getUserId());
        kyc.setKycId(kycId);
        kyc.setAadhaarFile(aadhaarPath);
        kyc.setPanFile(panPath);
        kyc.setBankStatement(bankPath);
        kyc.setSignature(signaturePath);

        KycDocument savedKyc = kycRepository.save(kyc);

        // Call OCR service synchronously (blocking) to get response before returning
        System.out.println("\n=== CALLING OCR SERVICE ===");
        System.out.println("KYC ID: " + kycId);
        OcrResponseDTO ocrResponse = ocrClient.processKycWithOcr(kycId, user.getUserId(), aadhaarPath, panPath,
                bankPath, signaturePath);
        System.out.println("=== OCR CALL COMPLETED ===");

        if (ocrResponse != null && ocrResponse.getKycStatus() != null) {
            System.out.println("Processing OCR response. Status: " + ocrResponse.getKycStatus());
            savedKyc.setStatus(ocrResponse.getKycStatus());
            
            // loginName is already extracted at the beginning
            System.out.println("KycService: Starting Name Matching process...");
            
            KycData kycData = kycDataRepository.findByKycId(kycId)
                    .orElseThrow(() -> {
                        System.err.println("KycService ERROR: KycData NOT FOUND for ID: " + kycId);
                        return new RuntimeException("KYC data not found in DB after OCR processing for ID: " + kycId);
                    });

            System.out.println("Retrieved extracted names from DB - Aadhaar: " + kycData.getAadhaarName() + ", PAN: " + kycData.getPanName());

            double aadhaarMatch = fuzzyMatcher.calculateSimilarity(loginName, kycData.getAadhaarName());
            double panMatch = fuzzyMatcher.calculateSimilarity(loginName, kycData.getPanName());

            System.out.println("=== Name Matching Results ===");
            System.out.println("Login Name: " + loginName);
            System.out.println("Aadhaar Name: " + kycData.getAadhaarName() + " (Score: " + String.format("%.2f", aadhaarMatch) + "%)");
            System.out.println("PAN Name: " + kycData.getPanName() + " (Score: " + String.format("%.2f", panMatch) + "%)");

            if (aadhaarMatch < 70.0 || panMatch < 70.0) {
                System.out.println("KYC FAILED due to name mismatch (Threshold: 70%)");
                savedKyc.setStatus("FAILED");
                kycRepository.save(savedKyc);
                throw new RuntimeException("KYC Failed: Name mismatch detected. " +
                        "(Aadhaar: " + String.format("%.1f", aadhaarMatch) + "%, " +
                        "PAN: " + String.format("%.1f", panMatch) + "%)");
            }

            System.out.println("KYC MATCH SUCCESSFUL. Finalizing report...");
            kycRepository.save(savedKyc);
        } else {
            System.out.println("WARNING: OCR Response is null or missing status!");
        }

        return ocrResponse;
    }

    private void validateFile(MultipartFile file, List<String> allowedExtensions) throws IOException {
        String filename = file.getOriginalFilename();
        if (filename == null)
            throw new RuntimeException("Invalid file");

        int lastDotIndex = filename.lastIndexOf('.');
        if (lastDotIndex == -1) {
            throw new RuntimeException("File has no extension: " + filename);
        }
        String extension = filename.substring(lastDotIndex + 1).toLowerCase();
        if (!allowedExtensions.contains(extension)) {
            throw new RuntimeException("Invalid file type: " + extension + ". Allowed: " + allowedExtensions);
        }

        // Try to read the file
        try {
            if (extension.equals("pdf")) {
                try (PDDocument doc = Loader.loadPDF(new RandomAccessReadBuffer(file.getInputStream()))) {
                    // If password protected, this will throw InvalidPasswordException
                } catch (InvalidPasswordException e) {
                    throw new RuntimeException("File is password-protected or unreadable");
                }
            } else {
                // For images
                BufferedImage img = ImageIO.read(file.getInputStream());
                if (img == null) {
                    throw new RuntimeException("File is password-protected or unreadable");
                }
            }
        } catch (IOException e) {
            throw new RuntimeException("File is password-protected or unreadable");
        }
    }

    private String saveFile(MultipartFile file, Path dir, String prefix) throws IOException {
        String filename = file.getOriginalFilename();
        int lastDotIndex = filename.lastIndexOf('.');
        String extension = (lastDotIndex != -1) ? filename.substring(lastDotIndex) : ".bin";
        String newFilename = prefix + extension;
        Path filePath = dir.resolve(newFilename);
        Files.copy(file.getInputStream(), filePath);
        return filePath.toString();
    }

    private String generateRandomString(int length) {
        String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt((int) (Math.random() * chars.length())));
        }
        return sb.toString();
    }
}