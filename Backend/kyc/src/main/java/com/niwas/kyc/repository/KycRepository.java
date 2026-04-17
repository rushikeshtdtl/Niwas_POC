package com.niwas.kyc.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import com.niwas.kyc.entity.KycDocument;
import com.niwas.kyc.dto.response.ComplianceKycReportDTO;
import java.util.Optional;
import java.util.List;

public interface KycRepository extends JpaRepository<KycDocument, Long> {

    boolean existsByKycId(String kycId);

    Optional<KycDocument> findByKycId(String kycId);

    @Query(value = "SELECT * FROM kyc_reports WHERE user_id = :userId ORDER BY timestamp DESC, id DESC LIMIT 1", nativeQuery = true)
    Optional<KycDocument> findLatestByUserId(@Param("userId") Long userId);

    @Query(value = "SELECT k.kyc_id, k.status, DATE_FORMAT(k.timestamp, '%Y-%m-%d'), u.name FROM kyc_reports k JOIN users u ON k.user_id = u.user_id ORDER BY k.timestamp DESC", nativeQuery = true)
    List<Object[]> findAllComplianceReportsRaw();
}