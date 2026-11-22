package com.vrevankar.alpha.fortune.market.repository;

import com.vrevankar.alpha.fortune.market.domain.entity.Exchange;
import com.vrevankar.alpha.fortune.market.domain.entity.ExchangeId;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

@Repository
public interface ExchangeRepo extends JpaRepository<Exchange, ExchangeId> {

    @Query(
            value = "SELECT e FROM Exchange e WHERE e.id.xchgDt = " +
                    "(SELECT MIN(sub.id.xchgDt) FROM Exchange sub " +
                    "WHERE sub.exchangeMaster = e.exchangeMaster) " +
                    "ORDER BY e.exchangeMaster.frCurr ASC, e.exchangeMaster.toCurr ASC",
            countQuery = "SELECT COUNT(DISTINCT e.exchangeMaster) FROM Exchange e"
    )
    Slice<Exchange> findDistinctCurrencyPairs(Pageable pageable);
}