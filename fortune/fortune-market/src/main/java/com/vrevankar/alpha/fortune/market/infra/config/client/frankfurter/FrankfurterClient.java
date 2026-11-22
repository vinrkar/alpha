package com.vrevankar.alpha.fortune.market.infra.config.client.frankfurter;

import com.vrevankar.alpha.fortune.market.domain.dto.ExchangeDto;
import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeHistoricReq;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class FrankfurterClient {

    private final RestClient restClient;
    private final String historyPath;
    private final String latestPath;

    public FrankfurterClient(
            @Qualifier("frankfurterRestClient") RestClient restClient,
            @Value("${external.frankfurter.history-path:/v1}") String historyPath,
            @Value("${external.frankfurter.latest-path:/v1/latest}") String latestPath) {
        this.restClient = restClient;
        this.historyPath = historyPath;
        this.latestPath = latestPath;
    }

    public List<ExchangeDto> fetchHistoricalRates(ExchangeHistoricReq req) {
        String uriPath = historyPath + "/{startDate}..{endDate}";

        Map<String, Object> response = restClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path(uriPath)
                        .queryParam("base", req.fromCurr())
                        .queryParam("symbols", req.toCurr())
                        .build(req.startDt().toString(), req.endDt().toString()))
                .retrieve()
                .body(new ParameterizedTypeReference<Map<String, Object>>() {});

        return mapResponseToDtos(response, req.fromCurr());
    }

    @SuppressWarnings("unchecked")
    private List<ExchangeDto> mapResponseToDtos(Map<String, Object> response, String s) {
        List<ExchangeDto> xchgRates = new ArrayList<>();

        if (response == null || !response.containsKey("rates")) {
            return xchgRates;
        }

        String baseCurrency = (String) response.getOrDefault("base", "USD");
        Map<String, Map<String, Number>> ratesByDate =
                (Map<String, Map<String, Number>>) response.get("rates");

        for (Map.Entry<String, Map<String, Number>> dateEntry : ratesByDate.entrySet()) {
            LocalDate date = LocalDate.parse(dateEntry.getKey());
            Map<String, Number> targetRates = dateEntry.getValue();

            if (targetRates != null && targetRates.containsKey("INR")) {
                Number rateValueNum = targetRates.get("INR");
                BigDecimal rateValue = rateValueNum != null
                        ? new BigDecimal(rateValueNum.toString())
                        : BigDecimal.ZERO;

                ExchangeDto dto = new ExchangeDto(
                        baseCurrency,
                        "INR",
                        date,
                        rateValue
                );
                xchgRates.add(dto);
            }
        }

        return xchgRates;
    }

    @SuppressWarnings("unchecked")
    public ExchangeDto fetchLatestRate() {
        Map<String, Object> response = restClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path(latestPath)
                        .queryParam("base", "USD")
                        .queryParam("symbols", "INR")
                        .build())
                .retrieve()
                .body(new ParameterizedTypeReference<Map<String, Object>>() {});

        if (response == null || !response.containsKey("rates")) {
            return null;
        }

        String baseCurrency = (String) response.getOrDefault("base", "USD");
        String dateStr = (String) response.get("date");
        LocalDate rateDate = LocalDate.parse(dateStr);

        Map<String, Number> targetRates = (Map<String, Number>) response.get("rates");
        if (targetRates != null && targetRates.containsKey("INR")) {
            BigDecimal rateValue = new BigDecimal(targetRates.get("INR").toString());
            return new ExchangeDto(baseCurrency, "INR", rateDate, rateValue);
        }

        return null;
    }
}