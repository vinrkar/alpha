package com.vrevankar.alpha.fortune.market.infra.config.client.yahoo;

import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

import static com.vrevankar.alpha.fortune.market.common.enums.Currency.INR;
import static com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceConstants.*;
import static com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceUtil.buildChartUri;
import static com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceUtil.extractCleanTicker;

@Slf4j
@Component
public class YahooFinanceClient {

    private final RestClient restClient;
    private final String searchPath;
    private final String chartPath;

    public YahooFinanceClient(
            @Qualifier("yahooFinanceRestClient") RestClient restClient,
            @Value("${external.yahoo-finance.search-path:/v1/finance/search}") String searchPath,
            @Value("${external.yahoo-finance.chart-path:/v8/finance/chart/{symbol}}") String chartPath) {
        this.restClient = restClient;
        this.searchPath = searchPath;
        this.chartPath = chartPath;
    }

    public Optional<YahooFinanceResp> fetchDetailsByIsin(String isin) {
        try {
            Map response = restClient.get()
                    .uri(uriBuilder -> uriBuilder
                            .path(searchPath)
                            .queryParam(YahooFinanceConstants.PARAM_Q, isin)
                            .build())
                    .retrieve()
                    .body(Map.class);

            if (response != null && response.containsKey(QUOTES)) {
                var quotes = (List<Map<String, Object>>) response.get(QUOTES);
                if (quotes != null && !quotes.isEmpty()) {
                    Map<String, Object> firstMatch = quotes.get(0);

                    String rawSymbol = (String) firstMatch.get(SYMBOL);
                    String cleanTicker = extractCleanTicker(rawSymbol);

                    YahooFinanceResp quote = new YahooFinanceResp(
                            cleanTicker,
                            (String) firstMatch.get(LONG_NAME),
                            (String) firstMatch.get(EXCHANGE),
                            (String) firstMatch.getOrDefault(CURRENCY, INR)
                    );

                    return Optional.of(quote);
                }
            }
        } catch (Exception e) {
            log.error("Failed to fetch enrichment data from Yahoo Finance for ISIN: {}", isin, e);
        }
        return Optional.empty();
    }

    public List<SecurityDto> fetchHistoricData(YahooFinanceReq yahooFinanceReq) {
        try {
            Map response = restClient.get()
                    .uri(buildChartUri(
                            chartPath, // Updated from properties.getChartPath()
                            yahooFinanceReq.ticker(),
                            yahooFinanceReq.xchg(),
                            yahooFinanceReq.startDt(),
                            yahooFinanceReq.endDt()
                    ))
                    .retrieve()
                    .body(Map.class);

            List<SecurityDto> historicPrices = parseChartResponse(response, yahooFinanceReq);
            log.info("Successfully parsed {} historic price points for ticker: {}", historicPrices.size(), yahooFinanceReq.ticker());
            return historicPrices;
        } catch (org.springframework.web.client.RestClientResponseException e) {
            log.warn("Ticker not found or HTTP error on Yahoo Finance for ticker: {} Status: {}", yahooFinanceReq.ticker(), e.getStatusCode());
            throw e;
        } catch (Exception e) {
            log.error("Failed to fetch historic market data from Yahoo Finance for ticker: {}", yahooFinanceReq.ticker(), e);
            throw new RuntimeException(e);
        }
    }

    public List<SecurityDto> fetchRoutineData(YahooFinanceReq yahooFinanceReq) {
        try {
            Map response = restClient.get()
                    .uri(buildChartUri(
                            chartPath, // Updated from properties.getChartPath()
                            yahooFinanceReq.ticker(),
                            yahooFinanceReq.xchg(),
                            null,
                            null
                    ))
                    .retrieve()
                    .body(Map.class);

            List<SecurityDto> routinePrices = parseChartResponse(response, yahooFinanceReq);

            // Reduce the 5-day rolling window to strictly the single latest trade date
            if (routinePrices != null && !routinePrices.isEmpty()) {
                SecurityDto latestCandle = routinePrices.stream()
                        .max(Comparator.comparing(SecurityDto::tradeDt))
                        .orElse(null);

                routinePrices = latestCandle != null ? List.of(latestCandle) : Collections.emptyList();
            }

            log.info("Successfully parsed latest routine price point for ticker: {}", yahooFinanceReq.ticker());
            return routinePrices;
        } catch (org.springframework.web.client.RestClientResponseException e) {
            log.warn("Ticker not found or HTTP error on Yahoo Finance for routine data: {} Status: {}", yahooFinanceReq.ticker(), e.getStatusCode());
            throw e;
        } catch (Exception e) {
            log.error("Failed to fetch routine market data from Yahoo Finance for ticker: {}", yahooFinanceReq.ticker(), e);
            return Collections.emptyList();
        }
    }

    public SecurityDto fetchCurrentQuote(YahooFinanceReq quoteReq) {
        try {
            Map response = restClient.get()
                    .uri(buildChartUri(
                            chartPath, // Updated from properties.getChartPath()
                            quoteReq.ticker(),
                            quoteReq.xchg(),
                            null,
                            null
                    ))
                    .retrieve()
                    .body(Map.class);

            List<SecurityDto> prices = parseChartResponse(response, quoteReq);
            if (!prices.isEmpty()) {
                return prices.stream()
                        .max(Comparator.comparing(SecurityDto::tradeDt))
                        .orElse(null);
            }
        } catch (org.springframework.web.client.RestClientResponseException e) {
            log.warn("Ticker not found or HTTP error on Yahoo Finance for quote: {} Status: {}", quoteReq.ticker(), e.getStatusCode());
            throw e;
        } catch (Exception e) {
            log.error("Failed to fetch live quote from Yahoo Finance for ticker: {}", quoteReq.ticker(), e);
        }
        return null;
    }

    private List<SecurityDto> parseChartResponse(Map response, YahooFinanceReq yahooFinanceReq) {
        List<SecurityDto> prices = new java.util.ArrayList<>();

        if (response != null && response.containsKey("chart")) {
            Map<String, Object> chart = (Map<String, Object>) response.get("chart");
            var resultList = (java.util.List<Map<String, Object>>) chart.get("result");

            if (resultList != null && !resultList.isEmpty()) {
                Map<String, Object> result = resultList.get(0);

                var timestamps = (java.util.List<Number>) result.get("timestamp");
                Map<String, Object> indicators = (Map<String, Object>) result.get("indicators");
                var quotes = (java.util.List<Map<String, Object>>) indicators.get("quote");

                if (timestamps != null && quotes != null && !quotes.isEmpty()) {
                    var closes = (java.util.List<Number>) quotes.get(0).get("close");

                    for (int i = 0; i < timestamps.size(); i++) {
                        Number ts = timestamps.get(i);
                        Number price = (closes != null && i < closes.size()) ? closes.get(i) : null;

                        if (ts != null && price != null) {
                            LocalDate tradeDate = java.time.Instant.ofEpochSecond(ts.longValue())
                                    .atZone(java.time.ZoneId.of("Asia/Kolkata"))
                                    .toLocalDate();

                            BigDecimal closePrice = BigDecimal.valueOf(price.doubleValue())
                                    .setScale(2, java.math.RoundingMode.HALF_UP);

                            prices.add(new SecurityDto(
                                    yahooFinanceReq.isin(),
                                    yahooFinanceReq.ticker(),
                                    tradeDate,
                                    closePrice
                            ));
                        }
                    }
                }
            }
        }
        return prices;
    }
}