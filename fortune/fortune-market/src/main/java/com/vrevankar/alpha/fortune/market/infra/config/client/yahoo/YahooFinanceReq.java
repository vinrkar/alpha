package com.vrevankar.alpha.fortune.market.infra.config.client.yahoo;

import com.vrevankar.alpha.fortune.market.domain.entity.SecurityMaster;

import java.time.LocalDate;

public record YahooFinanceReq(
        String isin,
        String xchg,
        LocalDate startDt,
        LocalDate endDt,
        String ticker
) {
    // 1. Used for HISTORICAL bulk loads (retains inception date)
    public static YahooFinanceReq from(SecurityMaster entity) {
        return new YahooFinanceReq(
                entity.getIsin(),
                entity.getXchg(),
                entity.getStartDt(),
                entity.getEndDt(),
                YahooFinanceUtil.computeTicker(entity.getTicker(), entity.getXchg())
        );
    }

    // 2. Used for LIVE / ON-DEMAND loads (automatically applies the 5-day lookback window)
    public static YahooFinanceReq fromLive(SecurityMaster entity) {
        LocalDate today = LocalDate.now();
        return new YahooFinanceReq(
                entity.getIsin(),
                entity.getXchg(),
                today.minusDays(5), // Safely covers weekends & holidays
                today,
                YahooFinanceUtil.computeTicker(entity.getTicker(), entity.getXchg())
        );
    }
}