package com.vrevankar.alpha.fortune.market.infra.config.batch;

import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceClient;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceReq;
import com.vrevankar.alpha.fortune.market.repository.SecurityMasterRepo;
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

@Configuration
@RequiredArgsConstructor
public class RoutineSecurityBatchConfig {

    private final BatchConfigSupport batchSupport;
    private final YahooFinanceClient yahooFinanceClient;
    private final SecurityMasterRepo securityMasterRepo;
    private final ProducerFactory<String, SecurityDto> producerFactory;

    @Bean
    public KafkaTemplate<String, SecurityDto> securityLiveKafkaTemplate(
            @Value("${fortune.kafka.topics.security-prices-live}") String topic) {
        KafkaTemplate<String, SecurityDto> template = new KafkaTemplate<>(producerFactory);
        template.setDefaultTopic(topic);
        return template;
    }

    @Bean
    public Job routineSecurityJob(JobRepository jobRepository,
                                  @Qualifier("routineSecurityStep") Step routineSecurityStep,
                                  SecurityIngestionStateListener stateListener) {
        return new JobBuilder("routineSecurityJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .listener(stateListener) // Registers the listener to update SECURITY_INGESTION_STATE on completion
                .start(routineSecurityStep)
                .build();
    }

    @Bean
    public Step routineSecurityStep(JobRepository jobRepository, PlatformTransactionManager transactionManager,
                                    @Qualifier("securityLiveKafkaTemplate") KafkaTemplate<String, SecurityDto> kafkaTemplate,
                                    @Value("${fortune.kafka.topics.security-prices-live}") String topic) {
        return batchSupport.buildStep(
                jobRepository, transactionManager, "routineSecurityStep",
                batchSupport.buildRepositoryReader(securityMasterRepo, "routineSecurityReader", "findActiveSecurities", "isin"),
                masterEntity -> yahooFinanceClient.fetchRoutineData(YahooFinanceReq.from(masterEntity)),
                batchSupport.buildSecurityKafkaWriter(kafkaTemplate, topic) // <--- Updated method name
        );
    }
}