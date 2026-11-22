package com.vrevankar.alpha.fortune.market.service.impl;

import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;
import com.vrevankar.alpha.fortune.market.domain.entity.SecurityMaster;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceClient;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceReq;
import com.vrevankar.alpha.fortune.market.repository.SecurityMasterRepo;
import com.vrevankar.alpha.fortune.market.service.SecurityService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
class SecurityServiceImpl implements SecurityService {

    private final YahooFinanceClient yahooFinanceClient;
    private final SecurityMasterRepo securityMasterRepo;

    @Qualifier("securityLiveKafkaTemplate")
    private final KafkaTemplate<String, SecurityDto> kafkaTemplate;

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