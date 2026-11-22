package com.vrevankar.alpha.fortune.market.infra.config.batch;

import com.vrevankar.alpha.fortune.market.domain.entity.SecurityIngestionState;
import com.vrevankar.alpha.fortune.market.repository.SecurityIngestionStateRepo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.BatchStatus;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobExecutionListener;
import org.springframework.stereotype.Component;

import java.time.LocalDate;

import static com.vrevankar.alpha.fortune.market.common.constants.SecurityConstants.ROUTINE_JOB_NAME;

@Component
@RequiredArgsConstructor
@Slf4j
public class SecurityIngestionStateListener implements JobExecutionListener {

    private final SecurityIngestionStateRepo securityIngestionStateRepo;

    @Override
    public void afterJob(JobExecution jobExecution) {
        if (jobExecution.getStatus() == BatchStatus.COMPLETED) {
            LocalDate tradeDt = jobExecution.getJobParameters().getLocalDate("tradeDt");
            if (tradeDt != null) {
                SecurityIngestionState state = securityIngestionStateRepo.findById(ROUTINE_JOB_NAME)
                        .orElseGet(() -> {
                            SecurityIngestionState newState = new SecurityIngestionState();
                            newState.setJobNm(ROUTINE_JOB_NAME);
                            return newState;
                        });

                state.setTradeDt(tradeDt.plusDays(1)); // Or advance based on your ingestion logic
                securityIngestionStateRepo.save(state);

                log.info("Successfully updated SECURITY_INGESTION_STATE for trade date: {}", tradeDt);
            }
        }
    }
}