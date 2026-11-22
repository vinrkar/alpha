package com.vrevankar.alpha.fortune.market.infra.config.batch;

import com.vrevankar.alpha.fortune.market.domain.dto.CurrencyPair;
import com.vrevankar.alpha.fortune.market.domain.dto.ExchangeDto;
import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeHistoricReq;
import com.vrevankar.alpha.fortune.market.domain.entity.ExchangeMaster;
import com.vrevankar.alpha.fortune.market.infra.config.client.frankfurter.FrankfurterClient;
import com.vrevankar.alpha.fortune.market.repository.ExchangeMasterRepo;
import lombok.RequiredArgsConstructor;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.launch.support.RunIdIncrementer;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.transaction.PlatformTransactionManager;

import java.time.LocalDate;

@Configuration
@RequiredArgsConstructor
public class HistoricExchangeBatchConfig {

    private final BatchConfigSupport batchSupport;
    private final FrankfurterClient frankfurterClient;
    private final ExchangeMasterRepo exchangeMasterRepo;
    private final ProducerFactory<String, ExchangeDto> producerFactory;
    private final ExchangeBatchSkipListener exchangeBatchSkipListener;

    @Bean
    public KafkaTemplate<String, ExchangeDto> historicExchangeKafkaTemplate(
            @Value("${fortune.kafka.topics.exchange-rates-hist:exchange.rates.hist-v1}") String topic) {
        KafkaTemplate<String, ExchangeDto> template = new KafkaTemplate<>(producerFactory);
        template.setDefaultTopic(topic);
        return template;
    }

    @Bean(name = "exchangeJob")
    public Job exchangeJob(JobRepository jobRepository,
                           @Qualifier("historicExchangeStep") Step historicExchangeStep) {
        return new JobBuilder("exchangeJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .start(historicExchangeStep)
                .build();
    }

    @Bean
    public Step historicExchangeStep(JobRepository jobRepository,
                                     PlatformTransactionManager transactionManager,
                                     @Qualifier("historicExchangeKafkaTemplate") KafkaTemplate<String, ExchangeDto> kafkaTemplate,
                                     @Value("${fortune.kafka.topics.exchange-rates-hist:exchange.rates.hist-v1}") String topic) {

        return batchSupport.buildStep(
                jobRepository, transactionManager, "historicExchangeStep",
                batchSupport.buildRepositoryReader(exchangeMasterRepo, "historicExchangeReader", "findByActive", "frCurr", "Y"),
                (ExchangeMaster masterEntity) -> {
                    // Dynamically retrieve job parameters
                    var stepExecution = org.springframework.batch.core.scope.context.StepSynchronizationManager.getContext().getStepExecution();
                    var jobParameters = stepExecution.getJobParameters();

                    String jobStartDt = jobParameters.getString("startDt");
                    String jobEndDt = jobParameters.getString("endDt");

                    LocalDate start = jobStartDt != null ? LocalDate.parse(jobStartDt) : LocalDate.now().minusYears(1);
                    LocalDate end = jobEndDt != null ? LocalDate.parse(jobEndDt) : LocalDate.now();

                    // FLIP THE PAIR: DB has INR -> USD, but we want USD -> INR for the API request
                    String apiBase = masterEntity.getToCurr();   // "USD"
                    String apiTarget = masterEntity.getFrCurr(); // "INR"

                    CurrencyPair invertedPair = new CurrencyPair(apiBase, apiTarget);
                    return frankfurterClient.fetchHistoricalRates(ExchangeHistoricReq.of(invertedPair, start, end));
                },
                batchSupport.buildExchangeKafkaWriter(kafkaTemplate, topic),
                exchangeBatchSkipListener
        );
    }
}