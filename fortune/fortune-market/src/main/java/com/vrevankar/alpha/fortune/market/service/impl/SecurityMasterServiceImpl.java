package com.vrevankar.alpha.fortune.market.service.impl;

import com.vrevankar.alpha.fortune.market.common.enums.Currency;
import com.vrevankar.alpha.fortune.market.common.enums.Exchange;
import com.vrevankar.alpha.fortune.market.common.enums.SecurityStatus;
import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import com.vrevankar.alpha.fortune.market.domain.dto.SecurityMasterDto;
import com.vrevankar.alpha.fortune.market.domain.dto.req.SecurityMasterPatchReq;
import com.vrevankar.alpha.fortune.market.domain.dto.req.SecurityMasterReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.SecurityMasterResp;
import com.vrevankar.alpha.fortune.market.domain.entity.SecurityMaster;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceClient;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceReq;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceResp;
import com.vrevankar.alpha.fortune.market.persistence.SecurityMasterDao;
import com.vrevankar.alpha.fortune.market.repository.SecurityMasterRepo;
import com.vrevankar.alpha.fortune.market.service.SecurityMasterService;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.text.WordUtils;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;

import static com.vrevankar.alpha.fortune.market.common.constants.SecurityConstants.UNKNOWN_VAL;
import static com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceUtil.extractCleanTicker;

@Slf4j
@Service
@RequiredArgsConstructor
class SecurityMasterServiceImpl implements SecurityMasterService {

    private final YahooFinanceClient yahooFinanceClient;
    private final SecurityMasterDao securityMasterDao;
    private final SecurityMasterRepo securityMasterRepo;

    @Qualifier("securityLiveKafkaTemplate")
    private final KafkaTemplate<String, SecurityDto> kafkaTemplate;

    private static final int MAX_RETRIES = 5;

    @Transactional
    public List<SecurityMasterResp> onboardSecurities(List<SecurityMasterReq> requests) {
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            var futures = requests.stream()
                    .map(request -> CompletableFuture.supplyAsync(() -> processSecurity(request), executor))
                    .toList();
                var entities = futures.stream()
                    .map(CompletableFuture::join)
                    .toList();
            return securityMasterDao.saveAll(entities).stream()
                    .map(this::mapToResponse)
                    .toList();
        }
    }

    @Transactional
    public SecurityMasterResp patchSecurity(String isin, SecurityMasterPatchReq request) {
        SecurityMaster security = securityMasterRepo.findByIsin(isin)
                .orElseThrow(() -> new EntityNotFoundException("Security not found for ISIN: " + isin));

        if (request.active() != null) {
            security.setActive(request.active());
            security.setEndDt(request.active() ? null : request.endDt() != null ? request.endDt() : LocalDate.now());
        } else if (request.endDt() != null) {
            security.setEndDt(request.endDt());
        }

        security.setUpdtDttm(LocalDateTime.now());
        SecurityMaster saved = securityMasterRepo.save(security);

        return mapToResponse(saved);
    }

    @Transactional(readOnly = true)
    public SecurityMasterResp getSecurityByIsin(String isin) {
        SecurityMaster entity = securityMasterDao.findByIsin(isin)
                .orElseThrow(() -> new RuntimeException("Security not found for ISIN: " + isin));
        return mapToResponse(entity);
    }

    @Transactional(readOnly = true)
    public List<SecurityMasterResp> getAllSecurities() {
        return securityMasterDao.findAll().stream()
                .map(this::mapToResponse)
                .toList();
    }

    @Transactional
    public void processPendingRetries() {
        LocalDateTime now = LocalDateTime.now();
        // Limit to 100 records per 5-minute execution cycle
        Pageable pageable = PageRequest.of(0, 100);

        List<SecurityMaster> pendingList = securityMasterRepo.findReadyForRetry(now, MAX_RETRIES, pageable);

        if (pendingList.isEmpty()) {
            return;
        }

        log.info("Found {} securities due for enrichment retry.", pendingList.size());

        for (SecurityMaster security : pendingList) {
            try {
                enrichAndUpsert(security);
                log.info("Successfully enriched security on retry: {}", security.getIsin());
            } catch (Exception e) {
                log.error("Enrichment retry failed for ISIN: {}. Attempt: {}", security.getIsin(), security.getRetryCount() + 1, e);
                handleRetryFailure(security);
            }
        }
    }

    @Transactional
    public void enrichAndUpsert(SecurityMaster security) {
        Optional<YahooFinanceResp> quoteOpt = yahooFinanceClient.fetchDetailsByIsin(security.getIsin());

        var enrichment = quoteOpt
                .map(q -> new SecurityMasterDto(
                        extractCleanTicker(q.ticker()),
                        q.secNm(),
                        q.xchg(),
                        normalizeCurrency(q.curr())
                ))
                .orElseGet(() -> SecurityMasterDto.fallback(security.getTicker()));

        if (!enrichment.isValid()) {
            throw new RuntimeException("Enrichment payload still invalid for ISIN: " + security.getIsin());
        }

        security.setTicker(enrichment.ticker());
        security.setSecNm(enrichment.secName());
        security.setXchg(enrichment.exchange());
        security.setCurr(enrichment.currency());
        security.setStatus(SecurityStatus.COMPLETED.name());
        security.setUpdtDttm(LocalDateTime.now());
        // Reset retry metadata upon success
        security.setRetryCount(0);
        security.setNextRetryAt(null);

        securityMasterRepo.save(security);
    }

    private SecurityMaster processSecurity(SecurityMasterReq request) {
        var quoteOpt = yahooFinanceClient.fetchDetailsByIsin(request.isin());

        return quoteOpt.map(quote -> {
            String rawTicker = quote.ticker();
            String exchange = quote.xchg();

            // 1. Infer exchange from ticker suffix if xchg is missing/null
            if ((exchange == null || exchange.isBlank() || exchange.equalsIgnoreCase("UNKNOWN"))
                    && rawTicker != null && rawTicker.contains(".")) {
                String[] parts = rawTicker.split("\\.");
                rawTicker = parts[0]; // Clean ticker: "EQUITASBNK"
                String suffix = parts[1];
                exchange = suffix.equalsIgnoreCase("BO") ? "BSE" : "NSE";
            }

            return SecurityMaster.builder()
                    .isin(request.isin())
                    .startDt(request.startDt())
                    .ticker(rawTicker) // Stored clean: "EQUITASBNK"
                    .secNm(WordUtils.capitalizeFully(quote.secNm()))
                    .xchg(Exchange.normalize(exchange)) // Stored valid: "NSE" or "BSE" (never UNKNOWN)
                    .curr(quote.curr() != null ? quote.curr() : "INR")
                    .status(SecurityStatus.COMPLETED.name())
                    .build();
        }).orElseGet(() -> {
            log.warn("Could not enrich security for ISIN: {} on initial onboard. Queuing for background retry.", request.isin());
            return SecurityMaster.builder()
                    .isin(request.isin())
                    .startDt(request.startDt())
                    .ticker(UNKNOWN_VAL)
                    .secNm(UNKNOWN_VAL)
                    .xchg(Exchange.NSE.name())
                    .curr(Currency.INR.name())
                    .status(SecurityStatus.PENDING_ENRICHMENT.name())
                    .retryCount(0)
                    .build();
        });
    }

    private String normalizeCurrency(String rawCurrency) {
        if (rawCurrency == null || rawCurrency.length() < 3) {
            return "INR";
        }
        return rawCurrency.substring(0, 3).toUpperCase();
    }

    private SecurityMasterResp mapToResponse(SecurityMaster entity) {
        return new SecurityMasterResp(
                entity.getSecId(),
                entity.getIsin(),
                entity.getTicker(),
                entity.getSecNm(),
                entity.getXchg(),
                entity.getCurr(),
                entity.getActive(),
                entity.getStartDt(),
                entity.getStatus(),
                entity.getCrtDttm(),
                entity.getUpdtDttm()
        );
    }

    private void handleRetryFailure(SecurityMaster security) {
        int currentRetries = security.getRetryCount() + 1;
        security.setRetryCount(currentRetries);
        security.setUpdtDttm(LocalDateTime.now());

        if (currentRetries >= MAX_RETRIES) {
            security.setStatus("FAILED");
            security.setNextRetryAt(null);
            log.warn("Security {} exceeded max retries ({}). Marked as FAILED.", security.getIsin(), MAX_RETRIES);
        } else {
            long backoffMinutes = (long) Math.pow(2, currentRetries);
            security.setNextRetryAt(LocalDateTime.now().plusMinutes(backoffMinutes));
            log.info("Scheduled next retry for ISIN {} in {} minutes.", security.getIsin(), backoffMinutes);
        }

        securityMasterRepo.save(security);
    }

    @Transactional
    public BatchLoadResp processOnDemandLiveLoad() {
        int size = 100;
        Pageable pageable = PageRequest.of(0, size);

        long totalProcessed = 0;
        long totalWritten = 0;
        long totalSkipped = 0;
        Map<String, String> writtenTickers = new LinkedHashMap<>();
        Map<String, Map<String, String>> skippedTickers = new LinkedHashMap<>();

        Slice<SecurityMaster> slice;
        do {
            slice = securityMasterRepo.findActiveSecurities(pageable);

            for (SecurityMaster entity : slice.getContent()) {
                totalProcessed++;
                try {
                    // Fetch single live quote
                    SecurityDto securityDto = yahooFinanceClient.fetchCurrentQuote(YahooFinanceReq.fromLive(entity));

                    if (securityDto != null && securityDto.isin() != null) {
                        kafkaTemplate.sendDefault(securityDto.isin(), securityDto);
                        totalWritten++;
                        writtenTickers.put(entity.getIsin(), entity.getTicker());
                    } else {
                        totalSkipped++;
                        skippedTickers.computeIfAbsent("Invalid Payload", k -> new LinkedHashMap<>())
                                .put(entity.getIsin(), "Fetched live quote was null");
                    }
                } catch (Exception e) {
                    totalSkipped++;
                    log.error("Failed to fetch/publish live data for ISIN: {}", entity.getIsin(), e);
                    skippedTickers.computeIfAbsent("API Fetch Error", k -> new LinkedHashMap<>())
                            .put(entity.getIsin(), e.getMessage());
                }
            }

            pageable = slice.nextPageable();
        } while (slice.hasNext());

        String status = (totalSkipped == 0) ? "COMPLETED" : (totalWritten > 0 ? "COMPLETED_WITH_SKIPS" : "FAILED");

        return new BatchLoadResp(status, totalProcessed, totalWritten, writtenTickers, totalSkipped, skippedTickers);
    }

}