package com.niwas.kyc.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.RestClientException;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.niwas.kyc.dto.response.OcrResponseDTO;
import com.niwas.kyc.model.User;
import com.niwas.kyc.repository.UserRepository;
import com.niwas.kyc.entity.KycData;
import com.niwas.kyc.entity.OcrResult;
import com.niwas.kyc.repository.KycDataRepository;
import com.niwas.kyc.repository.OcrResultRepository;
import java.util.UUID;
import java.io.File;

@Component
public class OcrClient {

    private static final Logger logger = LoggerFactory.getLogger(OcrClient.class);

    @Value("${ocr.service.base-url:http://192.168.0.200:8000}")
    private String ocrServiceBaseUrl;

    @Value("${ocr.mock-mode:false}")
    private boolean mockMode;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    private final KycDataRepository kycDataRepository;
    private final OcrResultRepository ocrResultRepository;
    private final UserRepository userRepository;

    public OcrClient(RestTemplate restTemplate, ObjectMapper objectMapper, KycDataRepository kycDataRepository,
            OcrResultRepository ocrResultRepository, UserRepository userRepository) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
        this.kycDataRepository = kycDataRepository;
        this.ocrResultRepository = ocrResultRepository;
        this.userRepository = userRepository;
    }

    public OcrResponseDTO processKycWithOcr(String kycId, Long userId, String aadhaarPath, String panPath,
            String bankPath,
            String signaturePath) {
        if (!mockMode) {
            try {
                String url = ocrServiceBaseUrl + "/kyc/validate";
                logger.info("Sending KYC documents to OCR service. URL: {}, KYC ID: {}", url, kycId);

                // Create multipart form data
                MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
                body.add("kyc_id", kycId);
                body.add("aadhaar_file", new org.springframework.core.io.FileSystemResource(new File(aadhaarPath)));
                body.add("pan_file", new org.springframework.core.io.FileSystemResource(new File(panPath)));
                body.add("bank_statement", new org.springframework.core.io.FileSystemResource(new File(bankPath)));
                body.add("live_signature", new org.springframework.core.io.FileSystemResource(new File(signaturePath)));

                // Set headers
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.MULTIPART_FORM_DATA);

                HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

                // Make API call
                String responseString = restTemplate.postForObject(url, requestEntity, String.class);
                JsonNode response = objectMapper.readTree(responseString);

                // Save OCR response to database
                KycData kycData = new KycData();
                kycData.setKycId(kycId);
                kycData.setUserId(userId);

                // Extract individual fields from ocr_data
                JsonNode ocrData = response.path("ocr_data");
                if (ocrData != null && !ocrData.isMissingNode()) {
                    // PAN Details
                    JsonNode panDetails = ocrData.path("pan_details");
                    if (panDetails != null && !panDetails.isMissingNode()) {
                        kycData.setPanNumber(panDetails.path("pan_number").asText(null));
                        kycData.setPanName(panDetails.path("pan_name").asText(null));
                        kycData.setPanDob(panDetails.path("pan_dob").asText(null));
                        kycData.setPanFatherName(panDetails.path("pan_father_name").asText(null));
                        kycData.setPanSignaturePath(panDetails.path("pan_signature_path").asText(null));
                    }

                    // Aadhaar Details
                    JsonNode aadhaarDetails = ocrData.path("aadhaar_details");
                    if (aadhaarDetails != null && !aadhaarDetails.isMissingNode()) {
                        kycData.setAadhaarNumber(aadhaarDetails.path("aadhaar_number").asText(null));
                        kycData.setAadhaarName(aadhaarDetails.path("aadhaar_name").asText(null));
                        kycData.setAadhaarDob(aadhaarDetails.path("aadhaar_dob").asText(null));
                        kycData.setAadhaarAddress(aadhaarDetails.path("aadhaar_address").asText(null));
                    }

                    // Statement Details
                    JsonNode statementDetails = ocrData.path("statement_details");
                    if (statementDetails != null && !statementDetails.isMissingNode()) {
                        kycData.setStatementName(statementDetails.path("statement_name").asText(null));
                        kycData.setStatementAccountNumber(
                                statementDetails.path("statement_account_number").asText(null));
                        kycData.setStatementIfscCode(statementDetails.path("statement_ifsc_code").asText(null));
                        kycData.setStatementAddress(statementDetails.path("statement_address").asText(null));
                    }

                    // Signature Details
                    JsonNode signatureDetails = ocrData.path("signature_details");
                    if (signatureDetails != null && !signatureDetails.isMissingNode()) {
                        kycData.setSignatureLivePath(signatureDetails.path("signature_live_path").asText(null));
                    }
                }

                kycDataRepository.save(kycData);
                logger.info("OCR response saved to database for KYC ID: {}", kycId);

                OcrResult ocrResult = new OcrResult();
                ocrResult.setUserId(userId);
                ocrResult.setKycId(kycId);
                ocrResult.setRequestId(response.path("request_id").asText(null));
                ocrResult.setKycStatus(response.path("kyc_status").asText(null));

                JsonNode kycScoresNode = response.path("kyc_scores");
                if (kycScoresNode != null && !kycScoresNode.isMissingNode()) {
                    ocrResult.setIdentityScore(kycScoresNode.path("identity_score").isNull() ? null
                            : kycScoresNode.path("identity_score").asInt());
                    ocrResult.setFraudScore(kycScoresNode.path("fraud_score").isNull() ? null
                            : kycScoresNode.path("fraud_score").asInt());
                    ocrResult.setRiskScore(kycScoresNode.path("risk_score").isNull() ? null
                            : kycScoresNode.path("risk_score").asInt());
                    ocrResult.setKycScoresSignatureMatchScore(kycScoresNode.path("signature_match_score").isNull() ? null
                            : kycScoresNode.path("signature_match_score").asDouble());
                    ocrResult.setFinalScore(kycScoresNode.path("final_score").isNull() ? null
                            : kycScoresNode.path("final_score").asDouble());
                }

                JsonNode kycMatchingNode = response.path("kyc_matching");
                if (kycMatchingNode != null && !kycMatchingNode.isMissingNode()) {
                    ocrResult.setPanToAadhaarNameScore(kycMatchingNode.path("pan_to_aadhaar_name_score").isNull() ? null
                            : kycMatchingNode.path("pan_to_aadhaar_name_score").asDouble());
                    ocrResult.setPanToStatementNameScore(
                            kycMatchingNode.path("pan_to_statement_name_score").isNull() ? null
                                    : kycMatchingNode.path("pan_to_statement_name_score").asDouble());
                    ocrResult.setAadhaarToStatementNameScore(
                            kycMatchingNode.path("aadhaar_to_statement_name_score").isNull() ? null
                                    : kycMatchingNode.path("aadhaar_to_statement_name_score").asDouble());
                    ocrResult.setAadhaarToStatementAddressScore(
                            kycMatchingNode.path("aadhaar_to_statement_address_score").isNull() ? null
                                    : kycMatchingNode.path("aadhaar_to_statement_address_score").asDouble());
                    ocrResult.setPanToAadhaarDobMatch(
                            kycMatchingNode.path("pan_to_aadhaar_dob_match").isNull() ? null
                                    : kycMatchingNode.path("pan_to_aadhaar_dob_match").asBoolean());
                    ocrResult.setKycMatchingSignatureMatchScore(
                            kycMatchingNode.path("signature_match_score").isNull() ? null
                                    : kycMatchingNode.path("signature_match_score").asDouble());
                }

                JsonNode kycValidationNode = response.path("kyc_validation");
                if (kycValidationNode != null && !kycValidationNode.isMissingNode()) {
                    ocrResult.setPanValidationStatus(
                            kycValidationNode.path("pan_validation_status").isNull() ? null
                                    : kycValidationNode.path("pan_validation_status").asBoolean());
                    ocrResult.setAadhaarValidationStatus(
                            kycValidationNode.path("aadhaar_validation_status").isNull() ? null
                                    : kycValidationNode.path("aadhaar_validation_status").asBoolean());
                    ocrResult.setStatementValidationStatus(
                            kycValidationNode.path("statement_validation_status").isNull() ? null
                                    : kycValidationNode.path("statement_validation_status").asBoolean());
                    ocrResult.setSignatureValidationStatus(
                            kycValidationNode.path("signature_validation_status").isNull() ? null
                                    : kycValidationNode.path("signature_validation_status").asBoolean());
                }

                JsonNode kycDecisionNode = response.path("kyc_decision");
                if (kycDecisionNode != null && !kycDecisionNode.isMissingNode()) {
                    ocrResult.setDecisionResult(kycDecisionNode.path("decision_result").asText(null));
                    ocrResult.setDecisionReason(kycDecisionNode.path("decision_reason").asText(null));
                }

                JsonNode ocrLogNode = response.path("ocr_log");
                if (ocrLogNode != null && !ocrLogNode.isMissingNode()) {
                    ocrResult.setOcrLogStatus(ocrLogNode.path("status").asText(null));
                    ocrResult.setOcrLogMessage(ocrLogNode.path("message").asText(null));
                }

                ocrResult.setProcessedTimestamp(response.path("processed_timestamp").asText(null));
                ocrResultRepository.save(ocrResult);
                logger.info("OCR summary saved to ocr_results for KYC ID: {}", kycId);

                // Extract response data to send to frontend
                String kycStatus = response.path("kyc_status").asText(null);

                OcrResponseDTO.KycScores kycScores = new OcrResponseDTO.KycScores();
                if (kycScoresNode != null && !kycScoresNode.isMissingNode()) {
                    kycScores.setIdentityScore(kycScoresNode.path("identity_score").asInt(0));
                    kycScores.setFraudScore(kycScoresNode.path("fraud_score").asInt(0));
                    kycScores.setRiskScore(kycScoresNode.path("risk_score").asInt(0));
                    kycScores.setSignatureMatchScore(kycScoresNode.path("signature_match_score").asDouble(0.0));
                    kycScores.setFinalScore(kycScoresNode.path("final_score").asDouble(0.0));
                }

                OcrResponseDTO ocrResponseDTO = new OcrResponseDTO(kycId, kycStatus, kycScores);

                // Log response
                String prettyResponseJson = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(response);
                logger.info("OCR RESPONSE for KYC ID {}: {}", kycId, prettyResponseJson);

                return ocrResponseDTO;

            } catch (RestClientException e) {
                if (e.getMessage() != null && e.getMessage().contains("Connection refused")) {
                    logger.error("Cannot connect to OCR service at {} for KYC ID {}", ocrServiceBaseUrl, kycId);
                    System.out.println("ERROR: OCR service unavailable at " + ocrServiceBaseUrl);
                } else if (e.getMessage() != null && e.getMessage().contains("timed out")) {
                    logger.error("OCR service timeout for KYC ID {}", kycId);
                    System.out.println("ERROR: OCR processing timeout for KYC ID: " + kycId);
                } else {
                    logger.error("OCR service error for KYC ID {}: {}", kycId, e.getMessage(), e);
                    System.out.println("ERROR: OCR service error - " + e.getMessage());
                }
                return null;
            } catch (Exception e) {
                logger.error("Unexpected error during OCR processing for KYC ID {}", kycId, e);
                System.out.println("ERROR: Unexpected error during OCR processing - " + e.getMessage());
                return null;
            }
        } else {
            // MOCK MODE
            logger.info("OCR Mock Mode enabled. Generating dummy response for KYC ID: {}", kycId);

            // Fetch user to get name for mock data
            User user = userRepository.findById(userId).orElse(null);
            String mockName = (user != null) ? user.getName() : "Mock User";

            // Save Mock KycData
            KycData kycData = new KycData();
            kycData.setKycId(kycId);
            kycData.setUserId(userId);
            kycData.setPanNumber("ABCDE1234F");
            kycData.setPanName(mockName);
            kycData.setPanDob("1990-01-01");
            kycData.setAadhaarNumber("123456789012");
            kycData.setAadhaarName(mockName);
            kycData.setAadhaarDob("1990-01-01");
            kycData.setAadhaarAddress("123 Mock Street, Mumbai, Maharashtra");
            kycData.setStatementName(mockName);
            kycData.setStatementAccountNumber("000011112222");
            kycData.setStatementIfscCode("MOCK0001234");
            kycDataRepository.save(kycData);

            // Save Mock OcrResult
            OcrResult ocrResult = new OcrResult();
            ocrResult.setUserId(userId);
            ocrResult.setKycId(kycId);
            ocrResult.setRequestId("MOCK-REQ-" + UUID.randomUUID().toString());
            ocrResult.setKycStatus("SUCCESS");
            ocrResult.setIdentityScore(100);
            ocrResult.setFraudScore(0);
            ocrResult.setRiskScore(0);
            ocrResult.setFinalScore(100.0);
            ocrResultRepository.save(ocrResult);

            OcrResponseDTO.KycScores kycScores = new OcrResponseDTO.KycScores(100, 0, 0, 100.0, 100.0);
            return new OcrResponseDTO(kycId, "SUCCESS", kycScores);
        }
    }
}
