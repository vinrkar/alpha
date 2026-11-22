package com.vrevankar.alpha.fortune.market.messaging;

import com.vrevankar.alpha.fortune.market.domain.dto.ExchangeDto;
import com.vrevankar.alpha.fortune.market.domain.entity.Exchange;
import com.vrevankar.alpha.fortune.market.domain.entity.ExchangeId;
import com.vrevankar.alpha.fortune.market.domain.entity.ExchangeMaster;
import com.vrevankar.alpha.fortune.market.repository.ExchangeMasterRepo;
import com.vrevankar.alpha.fortune.market.repository.ExchangeRepo;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;

@Component
@RequiredArgsConstructor
public class ExchangeConsumer {

    private static final Logger log = LoggerFactory.getLogger(ExchangeConsumer.class);

    private final ExchangeRepo exchangeRepo;
    private final ExchangeMasterRepo exchangeMasterRepo;

    @Transactional
    @KafkaListener(
            topics = "${fortune.kafka.topics.exchange-rates-hist:exchange.rates.hist-v1}",
            groupId = "${fortune.kafka.consumer.exchange-rates-hist-group:exchange-rates-hist-group}"
    )
    public void consumeHistoricExchangeRate(@Payload ExchangeDto dto) {
        processExchangeRate(dto, "Historic");
    }

    @Transactional
    @KafkaListener(
            topics = "${fortune.kafka.topics.exchange-rate-live:exchange.rate.live-v1}",
            groupId = "${fortune.kafka.consumer.exchange-rate-live-group:exchange-rate-live-group}"
    )
    public void consumeLiveExchangeRate(@Payload ExchangeDto dto) {
        processExchangeRate(dto, "Live");
    }

    private void processExchangeRate(ExchangeDto dto, String streamType) {
        try {
            // Flexible lookup: Tries USD -> INR, and if not found, falls back to checking INR -> USD
            ExchangeMaster master = exchangeMasterRepo.findByFrCurrAndToCurr(dto.frCurr(), dto.toCurr())
                    .orElseGet(() -> exchangeMasterRepo.findByFrCurrAndToCurr(dto.toCurr(), dto.frCurr())
                            .orElseThrow(() -> new IllegalStateException(
                                    String.format("Exchange master record not found for %s -> %s", dto.frCurr(), dto.toCurr())
                            )));

            ExchangeId id = new ExchangeId(master.getXchgId(), dto.xchgDt());
            Exchange existingEntity = exchangeRepo.findById(id).orElse(null);

            int scale = 4;
            BigDecimal incomingRate = dto.xchgRt().setScale(scale, RoundingMode.HALF_UP);

            if (existingEntity != null) {
                BigDecimal existingRate = existingEntity.getXchgRt().setScale(scale, RoundingMode.HALF_UP);

                if (existingRate.compareTo(incomingRate) == 0) {
                    log.debug("{} exchange rate unchanged ({}) for {} -> {}, skipping database upsert.",
                            streamType, incomingRate, dto.frCurr(), dto.toCurr());
                    return;
                }

                existingEntity.setXchgRt(incomingRate);
                existingEntity.setUpdtDttm(LocalDateTime.now());
            } else {
                existingEntity = Exchange.builder()
                        .id(id)
                        .exchangeMaster(master)
                        .xchgRt(incomingRate)
                        .updtDttm(LocalDateTime.now())
                        .build();
            }

            exchangeRepo.save(existingEntity);
            log.info("Successfully persisted/updated {} exchange rate for {} -> {} on {}: {}",
                    streamType, dto.frCurr(), dto.toCurr(), dto.xchgDt(), incomingRate);

        } catch (Exception e) {
            log.error("Failed to process {} exchange rate for {} -> {} on {}. Error: {}",
                    streamType, dto.frCurr(), dto.toCurr(), dto.xchgDt(), e.getMessage(), e);
            throw e;
        }
    }
}