package com.vrevankar.alpha.fortune.market.controller;

import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeBatchReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;
import com.vrevankar.alpha.fortune.market.service.ExchangeService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/exchange")
@RequiredArgsConstructor
@Slf4j
public class ExchangeController {

    private final ExchangeService exchangeService;

    @PostMapping("/load")
    public ResponseEntity<BatchLoadResp> triggerHistoricExchangeBatch(
            @RequestBody(required = false) @Valid ExchangeBatchReq request) {
        log.info("Received POST request to load historic exchange rate data.");

        BatchLoadResp response = exchangeService.runHistoricBatch(request);

        if ("FAILED".equals(response.executionStatus())) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }

        HttpStatus httpStatus = switch (response.executionStatus()) {
            case "COMPLETED" -> HttpStatus.OK;
            case "COMPLETED_WITH_SKIPS" -> HttpStatus.MULTI_STATUS;
            default -> HttpStatus.INTERNAL_SERVER_ERROR;
        };

        return ResponseEntity.status(httpStatus).body(response);
    }

    @PostMapping("/live")
    public ResponseEntity<String> triggerLiveExchangeRatePull() {
        log.info("Received on-demand REST request to pull and publish live exchange rates.");

        exchangeService.fetchAndPublishLiveRates();

        return ResponseEntity.accepted().body("Live exchange rate pull triggered and published to Kafka successfully.");
    }

}