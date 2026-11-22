package com.vrevankar.alpha.fortune.market.common.enums;

public enum Currency {
    INR,
    USD,
    UNKNOWN;

    public static Currency fromCode(String code) {
        if (code == null) {
            return UNKNOWN;
        }
        try {
            return Currency.valueOf(code.toUpperCase());
        } catch (IllegalArgumentException e) {
            return UNKNOWN;
        }
    }
}