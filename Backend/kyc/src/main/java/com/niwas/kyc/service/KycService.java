package com.niwas.kyc.service;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import com.niwas.kyc.entity.KycDocument;
import com.niwas.kyc.repository.KycRepository;
import com.niwas.kyc.repository.UserRepository;
import com.niwas.kyc.model.User;
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

    private static final String UPLOAD_DIR = "uploads/kyc/";

    public KycService(KycRepository kycRepository, UserRepository userRepository) {
        this.kycRepository = kycRepository;
        this.userRepository = userRepository;
    }

    public KycDocument uploadKyc(MultipartFile aadhaarFile, MultipartFile panFile, MultipartFile bankStatement,
            MultipartFile signature) throws IOException {
        // Get authenticated user
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        String mobile = (String) auth.getPrincipal();
        User user = userRepository.findByPhone(mobile).orElseThrow(() -> new RuntimeException("User not found"));

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
        String kycId;
        do {
            kycId = "KYC" + java.time.Year.now().getValue() + generateRandomString(6);
        } while (kycRepository.existsByKycId(kycId));

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

        return kycRepository.save(kyc);
    }

    private void validateFile(MultipartFile file, List<String> allowedExtensions) throws IOException {
        String filename = file.getOriginalFilename();
        if (filename == null)
            throw new RuntimeException("Invalid file");

        String extension = filename.substring(filename.lastIndexOf('.') + 1).toLowerCase();
        if (!allowedExtensions.contains(extension)) {
            throw new RuntimeException("Invalid file type");
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
        String extension = filename.substring(filename.lastIndexOf('.'));
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