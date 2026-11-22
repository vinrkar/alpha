package com.vrevankar.alpha.fortune.market.service.impl;

import com.vrevankar.alpha.fortune.market.domain.dto.ExchangeDto;
import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeBatchReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;
import com.vrevankar.alpha.fortune.market.infra.config.client.frankfurter.FrankfurterClient;
import com.vrevankar.alpha.fortune.market.repository.SecurityMasterRepo;
import com.vrevankar.alpha.fortune.market.service.ExchangeService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class ExchangeServiceImpl implements ExchangeService {

    private final JobLauncher jobLauncher;

    @Qualifier("exchangeJob")
    private final Job exchangeJob;

    private final SecurityMasterRepo securityMasterRepo;
    private final FrankfurterClient frankfurterClient;

    @Qualifier("exchangeLiveKafkaTemplate")
    private final KafkaTemplate<String, ExchangeDto> kafkaTemplate;

    @Value("${fortune.kafka.topics.exchange-rate-live:exchange.rate.live-v1}")
    private String exchangeLiveTopic;

    @Override
    public BatchLoadResp runHistoricBatch(ExchangeBatchReq request) {
        LocalDate startDate = (request != null && request.startDt() != null)
                ? request.startDt()
                : securityMasterRepo.findEarliestSecurityDate()
                  .orElse(LocalDate.now().minusYears(1));

        LocalDate endDate = (request != null && request.endDt() != null)
                ? request.endDt()
                : LocalDate.now();

        try {
            var jobParameters = new JobParametersBuilder()
                    .addString("startDt", startDate.toString())
                    .addString("endDt", endDate.toString())
                    .addLong("runTimestamp", System.currentTimeMillis())
                    .toJobParameters();

            JobExecution jobExecution = jobLauncher.run(exchangeJob, jobParameters);

            long totalProcessed = 0;
            long totalWritten = 0;
            long totalSkipped = 0;

            for (var stepExecution : jobExecution.getStepExecutions()) {
                totalProcessed += stepExecution.getReadCount();
                totalWritten += stepExecution.getWriteCount();
                totalSkipped += stepExecution.getSkipCount();
            }

            return new BatchLoadResp(
                    jobExecution.getStatus().name(),
                    totalProcessed,
                    totalWritten,
                    new HashMap<>(),
                    totalSkipped,
                    Collections.emptyMap()
            );

        } catch (Exception e) {
            log.error("Failed to start historic exchange rate batch job", e);
            return new BatchLoadResp(
                    "FAILED",
                    0L,
                    0L,
                    Collections.emptyMap(),
                    0L,
                    Map.of("EXCEPTION", Map.of("ERROR", e.getMessage()))
            );
        }
    }

    @Override
    public void fetchAndPublishLiveRates() {
        log.info("Fetching latest live exchange rate from Frankfurter client...");

        ExchangeDto dto = frankfurterClient.fetchLatestRate();

        if (dto != null) {
            String messageKey = dto.frCurr() + "_" + dto.toCurr();
            kafkaTemplate.send(exchangeLiveTopic, messageKey, dto);
            log.info("Successfully published live exchange rate for {} -> {} to Kafka topic: {}",
                    dto.frCurr(), dto.toCurr(), exchangeLiveTopic);
        } else {
            log.warn("Frankfurter client returned null or empty latest rate.");
        }
    }
}