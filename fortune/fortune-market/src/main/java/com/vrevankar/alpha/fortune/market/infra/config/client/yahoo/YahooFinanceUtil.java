package com.vrevankar.alpha.fortune.market.infra.config.client.yahoo;

import lombok.experimental.UtilityClass;
import org.springframework.web.util.UriBuilder;

import java.net.URI;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.function.Function;

@UtilityClass
public class YahooFinanceUtil {

    public static String extractCleanTicker(String rawSymbol) {
        return rawSymbol;
    }

    public static String formatTickerForExchange(String ticker, String exchange) {
        if (exchange != null && !exchange.isBlank() && !ticker.contains(".")) {
            String suffix = mapToSuffix(exchange);
            return !suffix.isEmpty() ? ticker.concat(".").concat(suffix) : ticker;
        }
        return ticker;
    }

    public static Function<UriBuilder, URI> buildChartUri(
            String chartPath, String ticker, String exchange, LocalDate startDt, LocalDate endDt) {

        String formattedTicker = formatTickerForExchange(ticker, exchange);

        return uriBuilder -> {
            var builder = uriBuilder.path(chartPath);

            if (startDt != null || endDt != null) {
                // Historic batch loads: Use precise epoch period bounds
                LocalDate effectiveStart = startDt != null ? startDt : LocalDate.now().minusDays(5);
                LocalDate effectiveEnd = endDt != null ? endDt : LocalDate.now();

                ZoneId exchangeZone = ZoneId.of("Asia/Kolkata");
                long period1 = effectiveStart.atStartOfDay(exchangeZone).toEpochSecond();
                long period2 = effectiveEnd.atTime(23, 59, 59).atZone(exchangeZone).toEpochSecond();

                builder.queryParam("interval", "1d")
                        .queryParam("period1", period1)
                        .queryParam("period2", period2);
            } else {
                // Live / Routine pulls: Use range=5d to hit Yahoo's recent quote cache
                // and guarantee Friday's close is returned for .NS tickers.
                builder.queryParam("range", "5d")
                        .queryParam("interval", "1d");
            }

            return builder.build(formattedTicker);
        };
    }

    private static long toEpochSecond(LocalDate date, boolean isEndDate) {
        ZoneId exchangeZone = ZoneId.of("Asia/Kolkata");
        LocalDate target = date != null ? date : (isEndDate ? LocalDate.now(exchangeZone) : LocalDate.of(2000, 1, 1));

        return isEndDate ?
                target.atTime(23, 59, 59).atZone(exchangeZone).toEpochSecond() :
                target.atStartOfDay(exchangeZone).toEpochSecond();
    }

    public static String mapToSuffix(String exchange) {
        if (exchange == null) {
            return "";
        }
        return switch (exchange.toUpperCase()) {
            case "BSE" -> "BO";
            case "NSE", "NSI" -> "NS";
            default -> "";
        };
    }

    public static String computeTicker(String ticker, String exchange) {
        String suffix = mapToSuffix(exchange);
        if (ticker != null && !ticker.contains(".") && !suffix.isEmpty()) {
            return ticker + "." + suffix;
        }
        return ticker;
    }
}