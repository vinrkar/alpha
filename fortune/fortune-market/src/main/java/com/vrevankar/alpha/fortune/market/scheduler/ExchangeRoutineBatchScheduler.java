package com.vrevankar.alpha.fortune.market.scheduler;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Component
public class ExchangeRoutineBatchScheduler {

    private static final Logger log = LoggerFactory.getLogger(ExchangeRoutineBatchScheduler.class);

    private final JobLauncher jobLauncher;
    private final Job routineExchangeJob;

    public ExchangeRoutineBatchScheduler(JobLauncher jobLauncher, Job routineExchangeJob) {
        this.jobLauncher = jobLauncher;
        this.routineExchangeJob = routineExchangeJob;
    }

    @Scheduled(
            cron = "${fortune.market.batch.exchange.routine.cron:0 0 17 * * MON-FRI}",
            zone = "${fortune.market.batch.timezone:Asia/Kolkata}"
    )
    public void scheduleRoutineExchangeLoad() {
        log.info("Triggering scheduled routine live exchange rate batch job.");
        try {
            JobParameters jobParameters = new JobParametersBuilder()
                    .addString("timestamp", LocalDateTime.now().toString())
                    .addLocalDate("xchgDt", LocalDate.now())
                    .addLong("time", System.currentTimeMillis())
                    .toJobParameters();

            jobLauncher.run(routineExchangeJob, jobParameters);
            log.info("Routine live exchange rate batch job successfully completed execution.");
        } catch (Exception e) {
            log.error("Failed to execute scheduled routine live exchange rate batch job", e);
        }
    }
}