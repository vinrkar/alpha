package com.vrevankar.alpha.fortune.market.scheduler;

import com.vrevankar.alpha.fortune.market.service.SecurityMasterService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class SecurityRetryScheduler {

    private final SecurityMasterService securityMasterService;

    @Scheduled(
            cron = "${fortune.market.batch.security.routine-retry.cron:*/30 * * * * *}",
            zone = "${fortune.market.batch.timezone:Asia/Kolkata}"
    )
    public void schedulePendingRetries() {
        log.debug("Triggering scheduled check for pending security retries.");
        securityMasterService.processPendingRetries();
    }
}
