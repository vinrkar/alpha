package com.vrevankar.alpha.fortune.market.infra.config.client.yahoo;

import lombok.AccessLevel;
import lombok.NoArgsConstructor;

@NoArgsConstructor(access = AccessLevel.PRIVATE)
public final class YahooFinanceConstants {

    // Request Query Parameters
    public static final String PARAM_Q = "q";

    // JSON Response Keys
    public static final String QUOTES = "quotes";
    public static final String SYMBOL = "symbol";
    public static final String LONG_NAME = "longname";
    public static final String EXCHANGE = "xchg";
    public static final String CURRENCY = "currency";
}