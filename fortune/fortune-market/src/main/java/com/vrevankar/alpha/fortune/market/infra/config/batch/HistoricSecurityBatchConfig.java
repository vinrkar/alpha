package com.vrevankar.alpha.fortune.market.infra.config.batch;

import com.vrevankar.alpha.fortune.market.domain.entity.SecurityMaster;
import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceClient;
import com.vrevankar.alpha.fortune.market.infra.config.client.yahoo.YahooFinanceReq;
import com.vrevankar.alpha.fortune.market.repository.SecurityMasterRepo;
import lombok.RequiredArgsConstructor;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
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
public class HistoricSecurityBatchConfig {

    private final BatchConfigSupport batchSupport;
    private final YahooFinanceClient yahooFinanceClient;
    private final SecurityMasterRepo securityMasterRepo;
    private final ProducerFactory<String, SecurityDto> producerFactory;
    private final BatchSkipListener batchSkipListener;

    @Bean
    public KafkaTemplate<String, SecurityDto> historicKafkaTemplate(
            @Value("${fortune.kafka.topics.security-prices-hist}") String topic) {
        KafkaTemplate<String, SecurityDto> template = new KafkaTemplate<>(producerFactory);
        template.setDefaultTopic(topic);
        return template;
    }

    @Bean(name = "securityJob")
    public Job securityJob(JobRepository jobRepository, Step securityStep) {
        return new JobBuilder("securityJob", jobRepository).start(securityStep).build();
    }

    @Bean
    public Step securityStep(JobRepository jobRepository, PlatformTransactionManager transactionManager,
                             @Qualifier("historicKafkaTemplate") KafkaTemplate<String, SecurityDto> kafkaTemplate,
                             @Value("${fortune.kafka.topics.security-prices-hist}") String topic) {
        return batchSupport.buildStep(
                jobRepository, transactionManager, "securityStep",
                batchSupport.buildRepositoryReader(securityMasterRepo, "securityReader", "findUnprocessedSecurities"),
                (SecurityMaster masterEntity) -> yahooFinanceClient.fetchHistoricData(YahooFinanceReq.from(masterEntity)),
                batchSupport.buildSecurityKafkaWriter(kafkaTemplate, topic), // <--- Updated method name
                batchSkipListener
        );
    }
}