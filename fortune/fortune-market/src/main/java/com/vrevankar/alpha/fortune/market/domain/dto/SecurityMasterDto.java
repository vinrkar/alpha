package com.vrevankar.alpha.fortune.market.domain.dto;

import static com.vrevankar.alpha.fortune.market.common.constants.SecurityConstants.UNKNOWN_VAL;

public record SecurityMasterDto(
        String ticker,
        String secName,
        String exchange,
        String currency
) {
    public static SecurityMasterDto fallback(String defaultTicker) {
        return new SecurityMasterDto(
                defaultTicker != null ? defaultTicker : UNKNOWN_VAL,
                UNKNOWN_VAL,
                "NSE",
                "INR"
        );
    }

    public boolean isValid() {
        return ! UNKNOWN_VAL.equals(ticker);
    }
}