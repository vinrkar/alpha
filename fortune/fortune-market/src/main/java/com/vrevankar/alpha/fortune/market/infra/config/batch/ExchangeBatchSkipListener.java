package com.vrevankar.alpha.fortune.market.infra.config.batch;

import com.vrevankar.alpha.fortune.market.domain.dto.ExchangeDto;
import com.vrevankar.alpha.fortune.market.domain.entity.ExchangeMaster;
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
public class ExchangeBatchSkipListener implements SkipListener<ExchangeMaster, List<ExchangeDto>> {

    @Override
    public void onSkipInProcess(ExchangeMaster item, Throwable t) {
        String reason = "404 Not Found";
        if (t.getMessage() != null && !t.getMessage().contains("404")) {
            reason = "Processing Error";
        }

        log.warn("Skipped Exchange item during processing - From: {}, To: {}, Reason: {}",
                item.getFrCurr(), item.getToCurr(), reason);

        var stepContext = StepSynchronizationManager.getContext();
        if (stepContext != null && stepContext.getStepExecution() != null) {
            ExecutionContext executionContext = stepContext.getStepExecution().getExecutionContext();

            @SuppressWarnings("unchecked")
            Map<String, List<Map<String, String>>> skippedMap =
                    (Map<String, List<Map<String, String>>>) executionContext.get("skippedExchangePairsMap");

            if (skippedMap == null) {
                skippedMap = new HashMap<>();
                executionContext.put("skippedExchangePairsMap", (java.io.Serializable) skippedMap);
            }

            skippedMap.computeIfAbsent(reason, k -> new ArrayList<>())
                    .add(Map.of(item.getFrCurr(), item.getToCurr()));
        }
    }
}