package com.niwas.kyc.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import com.niwas.kyc.entity.KycData;
import java.util.Optional;

public interface KycDataRepository extends JpaRepository<KycData, Long> {
    Optional<KycData> findByKycId(String kycId);
}