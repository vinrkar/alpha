package com.vrevankar.alpha.fortune.market.infra.config.batch;

import com.vrevankar.alpha.fortune.market.domain.dto.ExchangeDto;
import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import org.springframework.batch.core.SkipListener;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.scope.context.StepSynchronizationManager;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ExecutionContext;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.ItemWriter;
import org.springframework.batch.item.data.RepositoryItemReader;
import org.springframework.batch.item.data.builder.RepositoryItemReaderBuilder;
import org.springframework.batch.item.kafka.KafkaItemWriter;
import org.springframework.batch.item.kafka.builder.KafkaItemWriterBuilder;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.web.client.RestClientResponseException;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Component
public class BatchConfigSupport {

    // --- Generic Step Builders (Supports any Entity and Dto type) ---
    public <E, D> Step buildStep(JobRepository jobRepository, PlatformTransactionManager transactionManager,
                                 String stepName, RepositoryItemReader<E> reader,
                                 ItemProcessor<E, List<D>> processor,
                                 ItemWriter<List<D>> writer) {
        return new StepBuilder(stepName, jobRepository)
                .<E, List<D>>chunk(10, transactionManager)
                .reader(reader)
                .processor(processor)
                .writer(writer)
                .build();
    }

    public <E, D> Step buildStep(JobRepository jobRepository, PlatformTransactionManager transactionManager,
                                 String stepName, RepositoryItemReader<E> reader,
                                 ItemProcessor<E, List<D>> processor,
                                 ItemWriter<List<D>> writer,
                                 SkipListener<E, List<D>> skipListener) {
        return new StepBuilder(stepName, jobRepository)
                .<E, List<D>>chunk(10, transactionManager)
                .reader(reader)
                .processor(processor)
                .writer(writer)
                .faultTolerant()
                .skip(RestClientResponseException.class)
                .skipLimit(100)
                .listener(skipListener)
                .build();
    }

    public <T, R extends JpaRepository<T, ?>> RepositoryItemReader<T> buildRepositoryReader(
            R repository, String name, String methodName) {
        return buildRepositoryReader(repository, name, methodName, "id");
    }

    // Add this overloaded version to support parameterized queries (like findByActive)
    public <T, R extends JpaRepository<T, ?>> RepositoryItemReader<T> buildRepositoryReader(
            R repository, String name, String methodName, String sortField, Object... arguments) {
        return new RepositoryItemReaderBuilder<T>()
                .name(name)
                .repository(repository)
                .methodName(methodName)
                .pageSize(50)
                .arguments(Arrays.asList(arguments)) // <--- Passes the query parameters (e.g., "Y")
                .sorts(Map.of(sortField, Sort.Direction.ASC))
                .build();
    }

    // Specific for Security Pipeline (keeps your execution context logic intact)
    public ItemWriter<List<SecurityDto>> buildSecurityKafkaWriter(KafkaTemplate<String, SecurityDto> kafkaTemplate, String topic) {
        KafkaItemWriter<String, SecurityDto> delegateWriter = new KafkaItemWriterBuilder<String, SecurityDto>()
                .kafkaTemplate(kafkaTemplate)
                .itemKeyMapper(dto -> dto.isin() + "_" + dto.tradeDt())
                .build();

        return items -> {
            for (List<SecurityDto> dtoList : items) {
                if (dtoList != null && !dtoList.isEmpty()) {
                    delegateWriter.write(new org.springframework.batch.item.Chunk<>(dtoList));

                    var stepContext = StepSynchronizationManager.getContext();
                    if (stepContext != null && stepContext.getStepExecution() != null) {
                        ExecutionContext executionContext = stepContext.getStepExecution().getExecutionContext();
                        @SuppressWarnings("unchecked")
                        List<Map<String, String>> writtenList =
                                (List<Map<String, String>>) executionContext.get("writtenTickersList");

                        if (writtenList == null) {
                            writtenList = new ArrayList<>();
                            executionContext.put("writtenTickersList", (java.io.Serializable) writtenList);
                        }

                        SecurityDto firstDto = dtoList.get(0);
                        Map<String, String> entry = Map.of(firstDto.isin(), firstDto.ticker());
                        if (!writtenList.contains(entry)) {
                            writtenList.add(entry);
                        }
                    }
                }
            }
        };
    }

    public ItemWriter<List<ExchangeDto>> buildExchangeKafkaWriter(KafkaTemplate<String, ExchangeDto> kafkaTemplate, String topic) {
        KafkaItemWriter<String, ExchangeDto> delegateWriter = new KafkaItemWriterBuilder<String, ExchangeDto>()
                .kafkaTemplate(kafkaTemplate)
                .itemKeyMapper(dto -> dto.frCurr() + "_" + dto.toCurr() + "_" + dto.xchgDt())
                .build();

        return items -> {
            for (List<ExchangeDto> dtoList : items) {
                if (dtoList != null && !dtoList.isEmpty()) {
                    delegateWriter.write(new org.springframework.batch.item.Chunk<>(dtoList));
                }
            }
        };
    }
}