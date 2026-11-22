package com.vrevankar.alpha.fortune.market.infra.config.client.yahoo;

public record YahooFinanceResp(
        String ticker,
        String secNm,
        String xchg,
        String curr
) {}