package com.vrevankar.alpha.fortune.market.scheduler;

import com.vrevankar.alpha.fortune.market.domain.entity.SecurityIngestionState;
import com.vrevankar.alpha.fortune.market.repository.SecurityIngestionStateRepo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.LocalDateTime;

import static com.vrevankar.alpha.fortune.market.common.constants.SecurityConstants.ROUTINE_JOB_NAME;

@Slf4j
@Component
@RequiredArgsConstructor
public class SecurityRoutineBatchScheduler {

    private final JobLauncher jobLauncher;
    private final Job routineSecurityJob;
    private final SecurityIngestionStateRepo securityIngestionStateRepo; // Injected to read checkpoint

    @Scheduled(
            cron = "${fortune.market.batch.security.routine.cron:*/30 * * * * *}",
            zone = "${fortune.market.batch.timezone:Asia/Kolkata}"
    )
    public void scheduleRoutineLoad() {
        log.info("Triggering scheduled routine live data batch job.");
        try {
            LocalDate lastTradeDt = securityIngestionStateRepo.findById(ROUTINE_JOB_NAME)
                    .map(SecurityIngestionState::getTradeDt)
                    .orElseGet(LocalDate::now);

            JobParameters jobParameters = new JobParametersBuilder()
                    .addString("timestamp", LocalDateTime.now().toString())
                    .addLocalDate("tradeDt", lastTradeDt)
                    .addLong("time", System.currentTimeMillis())
                    .toJobParameters();

            jobLauncher.run(routineSecurityJob, jobParameters);
            log.info("Routine live data batch job successfully completed scheduling execution for trade date: {}", lastTradeDt);
        } catch (Exception e) {
            log.error("Failed to execute scheduled routine live data batch job", e);
        }
    }
}