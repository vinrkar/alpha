package com.vrevankar.alpha.fortune.market.repository;

import com.vrevankar.alpha.fortune.market.domain.entity.SecurityMaster;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface SecurityMasterRepo extends JpaRepository<SecurityMaster, UUID> {

    Optional<SecurityMaster> findByIsin(String isin);

    Optional<SecurityMaster> findByTicker(String ticker);

    List<SecurityMaster> findByStatus(String status, Pageable pageable);

    boolean existsByIsin(String isin);

    @Query("SELECT s FROM SecurityMaster s WHERE s.status = 'PENDING_ENRICHMENT' " +
            "AND s.retryCount < :maxRetries " +
            "AND (s.nextRetryAt IS NULL OR s.nextRetryAt <= :currentTime)")
    List<SecurityMaster> findReadyForRetry(
            @Param("currentTime") LocalDateTime currentTime,
            @Param("maxRetries") int maxRetries,
            Pageable pageable
    );

    @Query("SELECT s FROM SecurityMaster s WHERE s.status = 'COMPLETED' " +
            "AND s.startDt IS NOT NULL " +
            "AND NOT EXISTS (SELECT m FROM Security m WHERE m.isin = s.isin)")
    Page<SecurityMaster> findUnprocessedSecurities(Pageable pageable);

    @Query("SELECT s FROM SecurityMaster s WHERE s.status = 'COMPLETED' AND s.active = true")
    Slice<SecurityMaster> findActiveSecurities(Pageable pageable);

    @Query("SELECT MIN(m.startDt) FROM SecurityMaster m")
    Optional<LocalDate> findEarliestSecurityDate();

}