package com.vrevankar.alpha.fortune.client.scheduler;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class AddressValScheduler {

    private final JobLauncher jobLauncher;
    private final Job addressValidationJob;

    @Scheduled(cron = "${spring.batch.address.routine.cron}")
    public void triggerRoutineAddressValidation() {
        log.info("Executing routine address validation job...");
        runJob("routine-run");
    }

    @Scheduled(cron = "${spring.batch.address.routine-retry.cron}")
    public void triggerFailedAddressRetry() {
        log.info("Executing failed address retry batch job...");
        runJob("retry-run");
    }

    private void runJob(String runType) {
        try {
            JobParameters jobParameters = new JobParametersBuilder()
                    .addString("runType", runType)
                    .addLong("runTime", System.currentTimeMillis())
                    .toJobParameters();

            JobExecution execution = jobLauncher.run(addressValidationJob, jobParameters);
            log.info("Job execution [{}] finished with status: {}", runType, execution.getStatus());
        } catch (Exception e) {
            log.error("Failed to execute address validation job [{}]: {}", runType, e.getMessage(), e);
        }
    }
}