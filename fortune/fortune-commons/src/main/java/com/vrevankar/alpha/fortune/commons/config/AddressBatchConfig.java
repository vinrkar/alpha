package com.vrevankar.alpha.fortune.commons.config;

import com.vrevankar.alpha.fortune.commons.client.AddressValClient;
import com.vrevankar.alpha.fortune.commons.entity.Address;
import com.vrevankar.alpha.fortune.commons.enums.AddressStatus;
import jakarta.persistence.EntityManagerFactory;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.database.JpaItemWriter;
import org.springframework.batch.item.database.JpaPagingItemReader;
import org.springframework.batch.item.database.builder.JpaItemWriterBuilder;
import org.springframework.batch.item.database.builder.JpaPagingItemReaderBuilder;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.transaction.PlatformTransactionManager;

import java.util.List;
import java.util.Map;

@AutoConfiguration
@RequiredArgsConstructor
@Slf4j
public class AddressBatchConfig {

    private final EntityManagerFactory entityManagerFactory;
    private final AddressValClient addressValClient;

    @Bean
    public JpaPagingItemReader<Address> addressReader() {
        return new JpaPagingItemReaderBuilder<Address>()
                .name("addressReader")
                .entityManagerFactory(entityManagerFactory)
                // Pull fresh pending records and transient failures eligible for retry
                .queryString("SELECT a FROM Address a WHERE a.status IN (:statuses)")
                .parameterValues(Map.of("statuses", List.of(AddressStatus.PENDING_ENRICHMENT, AddressStatus.FAILED)))
                .pageSize(10)
                .build();
    }

    @Bean
    public ItemProcessor<Address, Address> addressProcessor() {
        return address -> {
            log.info("Processing address enrichment for ID: {}", address.getAddrId());

            try {
                // Call external third-party validation API
                boolean isValid = addressValClient.validateAddress(
                        address.getStreet(), address.getCity(), address.getPin(), address.getIsoCd());

                if (isValid) {
                    address.setStatus(AddressStatus.COMPLETED);
                    log.info("Address ID {} successfully validated and COMPLETED", address.getAddrId());
                } else {
                    // Terminal business/format rejection from provider
                    address.setStatus(AddressStatus.FAILED_PERMANENTLY);
                    log.warn("Address ID {} permanently rejected by validation provider", address.getAddrId());
                }
            } catch (Exception e) {
                // Network or infrastructure timeout -> mark as FAILED for subsequent retry
                address.setStatus(AddressStatus.FAILED);
                log.error("Transient error while enriching Address ID {}: {}", address.getAddrId(), e.getMessage());
            }

            return address;
        };
    }

    @Bean
    public JpaItemWriter<Address> addressWriter() {
        return new JpaItemWriterBuilder<Address>()
                .entityManagerFactory(entityManagerFactory)
                .build();
    }

    @Bean
    public Step validateAddressStep(JobRepository jobRepository,
                                    PlatformTransactionManager transactionManager,
                                    JpaPagingItemReader<Address> addressReader,
                                    ItemProcessor<Address, Address> addressProcessor,
                                    JpaItemWriter<Address> addressWriter) {
        return new StepBuilder("validateAddressStep", jobRepository)
                .<Address, Address>chunk(10, transactionManager)
                .reader(addressReader)
                .processor(addressProcessor)
                .writer(addressWriter)
                .build();
    }

    @Bean
    public Job addressValidationJob(JobRepository jobRepository, Step validateAddressStep) {
        return new JobBuilder("addressValidationJob", jobRepository)
                .start(validateAddressStep)
                .build();
    }
}