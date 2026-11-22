package com.vrevankar.alpha.fortune.market.repository;

import com.vrevankar.alpha.fortune.market.domain.entity.ExchangeMaster;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ExchangeMasterRepo extends JpaRepository<ExchangeMaster, Long> {

    Optional<ExchangeMaster> findByFrCurrAndToCurr(String frCurr, String toCurr);

    List<ExchangeMaster> findByActive(String active);

    // Add this for Spring Batch paging support:
    Slice<ExchangeMaster> findByActive(String active, Pageable pageable);
}