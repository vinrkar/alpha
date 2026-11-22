package com.vrevankar.alpha.fortune.market.domain.dto.req;

import com.vrevankar.alpha.fortune.market.domain.dto.CurrencyPair;

import java.time.LocalDate;

public record ExchangeHistoricReq(
        String fromCurr,
        String toCurr,
        LocalDate startDt,
        LocalDate endDt
) {
    // 1. Used for default / full-history loads (1999 to present)
    public static ExchangeHistoricReq from(CurrencyPair currencyPair) {
        return new ExchangeHistoricReq(
                currencyPair.frCurr(),
                currencyPair.toCurr(),
                LocalDate.of(1999, 1, 1),
                LocalDate.now()
        );
    }

    // 2. Used for custom / bounded historic batch loads
    public static ExchangeHistoricReq of(CurrencyPair currencyPair, LocalDate startDt, LocalDate endDt) {
        return new ExchangeHistoricReq(
                currencyPair.frCurr(),
                currencyPair.toCurr(),
                startDt,
                endDt
        );
    }
}