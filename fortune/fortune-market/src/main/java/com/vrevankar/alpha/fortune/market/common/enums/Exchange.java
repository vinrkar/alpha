package com.vrevankar.alpha.fortune.market.common.enums;

public enum Exchange {
    NSE,
    NSI,
    UNKNOWN;

    public static String normalize(String exchange) {
        if (exchange == null || exchange.isBlank()) {
            return UNKNOWN.name();
        }
        return "NSI".equalsIgnoreCase(exchange) ? NSE.name() : exchange.toUpperCase();
    }
}