package com.vrevankar.alpha.fortune.market.infra.config.batch;

import com.vrevankar.alpha.fortune.market.domain.dto.ExchangeDto;
import com.vrevankar.alpha.fortune.market.infra.config.client.frankfurter.FrankfurterClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.launch.support.RunIdIncrementer;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.repeat.RepeatStatus;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration
@RequiredArgsConstructor
@Slf4j
public class RoutineExchangeBatchConfig {

    private final FrankfurterClient frankfurterClient;
    private final ProducerFactory<String, ExchangeDto> producerFactory;

    @Bean
    public KafkaTemplate<String, ExchangeDto> exchangeLiveKafkaTemplate(
            @Value("${fortune.kafka.topics.exchange-rate-live:exchange.rate.live-v1}") String topic) {
        KafkaTemplate<String, ExchangeDto> template = new KafkaTemplate<>(producerFactory);
        template.setDefaultTopic(topic);
        return template;
    }

    @Bean
    public Job routineExchangeJob(JobRepository jobRepository,
                                  @Qualifier("routineExchangeRateStep") Step routineExchangeRateStep) {
        return new JobBuilder("routineExchangeRateJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .start(routineExchangeRateStep)
                .build();
    }

    @Bean
    public Step routineExchangeRateStep(JobRepository jobRepository,
                                  PlatformTransactionManager transactionManager,
                                  @Qualifier("exchangeLiveKafkaTemplate") KafkaTemplate<String, ExchangeDto> kafkaTemplate,
                                  @Value("${fortune.kafka.topics.exchange-rate-live:exchange.rate.live-v1}") String topic) {
        return new StepBuilder("routineExchangeRateStep", jobRepository)
                .tasklet((contribution, chunkContext) -> {
                    log.info("Executing routine Exchange tasklet step. Calling Frankfurter API...");
                    ExchangeDto dto = frankfurterClient.fetchLatestRate();

                    if (dto != null) {
                        String key = dto.frCurr() + "_" + dto.toCurr() + "_" + dto.xchgDt();
                        log.info("Fetched live Exchange rate: {} -> {}. Publishing to Kafka topic: {}", key, dto.xchgRt(), topic);

                        try {
                            // Synchronous send to force immediate publishing and catch any errors/serialization issues
                            var result = kafkaTemplate.send(topic, key, dto).get();
                            kafkaTemplate.flush();
                            log.info("Successfully published to Kafka! Partition: {}, Offset: {}",
                                    result.getRecordMetadata().partition(),
                                    result.getRecordMetadata().offset());
                        } catch (Exception e) {
                            log.error("Failed to publish live Exchange rate to Kafka topic: {}", topic, e);
                            throw new RuntimeException("Kafka publication failed", e);
                        }

                    } else {
                        log.warn("Frankfurter API returned null for latest rate fetch.");
                    }

                    return RepeatStatus.FINISHED;
                }, transactionManager)
                .build();
    }
}