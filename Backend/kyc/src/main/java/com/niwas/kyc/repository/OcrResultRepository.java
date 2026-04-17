package com.niwas.kyc.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import com.niwas.kyc.entity.OcrResult;
import java.util.Optional;

public interface OcrResultRepository extends JpaRepository<OcrResult, Long> {
    Optional<OcrResult> findByKycId(String kycId);
}
