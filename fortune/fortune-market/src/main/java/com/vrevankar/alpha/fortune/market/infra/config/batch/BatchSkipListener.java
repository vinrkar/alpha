package com.vrevankar.alpha.fortune.market.infra.config.batch;

import com.vrevankar.alpha.fortune.market.domain.entity.SecurityMaster;
import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.SkipListener;
import org.springframework.batch.core.scope.context.StepSynchronizationManager;
import org.springframework.batch.item.ExecutionContext;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class BatchSkipListener implements SkipListener<SecurityMaster, List<SecurityDto>> {

    @Override
    public void onSkipInProcess(SecurityMaster item, Throwable t) {
        String reason = "404 Not Found";
        if (t.getMessage() != null && !t.getMessage().contains("404")) {
            reason = "Processing Error";
        }

        log.warn("Skipped item during processing - Ticker: {}, ISIN: {}, Reason: {}", item.getTicker(), item.getIsin(), reason);

        var stepContext = StepSynchronizationManager.getContext();
        if (stepContext != null && stepContext.getStepExecution() != null) {
            ExecutionContext executionContext = stepContext.getStepExecution().getExecutionContext();

            @SuppressWarnings("unchecked")
            Map<String, List<Map<String, String>>> skippedMap =
                    (Map<String, List<Map<String, String>>>) executionContext.get("skippedTickersMap");

            if (skippedMap == null) {
                skippedMap = new HashMap<>();
                executionContext.put("skippedTickersMap", (java.io.Serializable) skippedMap);
            }

            skippedMap.computeIfAbsent(reason, k -> new ArrayList<>())
                    .add(Map.of(item.getIsin(), item.getTicker()));
        }
    }
}