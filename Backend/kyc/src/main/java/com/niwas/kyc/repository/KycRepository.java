package com.niwas.kyc.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import com.niwas.kyc.entity.KycDocument;

public interface KycRepository extends JpaRepository<KycDocument, Long> {

    boolean existsByKycId(String kycId);
}