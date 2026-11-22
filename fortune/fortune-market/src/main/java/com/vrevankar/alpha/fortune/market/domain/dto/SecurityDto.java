package com.vrevankar.alpha.fortune.market.domain.dto;

import java.math.BigDecimal;
import java.time.LocalDate;

public record SecurityDto(
        String isin,
        String ticker,
        LocalDate tradeDt,
        BigDecimal price
) {
    public boolean isValid() {
        return isin != null && !isin.isBlank() && tradeDt != null && price != null;
    }
}