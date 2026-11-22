package com.vrevankar.alpha.fortune.market.messaging;

import com.vrevankar.alpha.fortune.market.domain.entity.Security;
import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import com.vrevankar.alpha.fortune.market.repository.SecurityRepo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class SecurityConsumer {

    private final SecurityRepo securityRepo;

    @Transactional
    @KafkaListener(topics = "${fortune.kafka.topics.security-prices-hist}", groupId = "${fortune.kafka.consumer.security-prices-hist-group}")
    public void consumeHistoricPrice(SecurityDto dto) {
        processPrice(dto, "Historic");
    }

    @Transactional
    @KafkaListener(
            topics = "${fortune.kafka.topics.security-prices-live}",
            groupId = "${fortune.kafka.consumer.security-prices-live-group}"
    )
    public void consumeLivePrice(SecurityDto dto) {
        processPrice(dto, "Live");
    }

    private void processPrice(SecurityDto dto, String streamType) {
        try {
            Security entity = Security.from(dto);
            securityRepo.save(entity);
            log.debug("Successfully upserted {} price point for ISIN: {} on Date: {}", streamType, dto.isin(), dto.tradeDt());
        } catch (Exception e) {
            log.error("Failed to process {} price point for ISIN: {}. Error: {}", streamType, dto.isin(), e.getMessage(), e);
            throw e;
        }
    }
}