package com.vrevankar.alpha.fortune.market.util;

import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;
import lombok.AccessLevel;
import lombok.NoArgsConstructor;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.StepExecution;
import org.springframework.batch.item.ExecutionContext;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@NoArgsConstructor(access = AccessLevel.PRIVATE)
public class BatchResponseMapper {

    public static BatchLoadResp mapToResponse(JobExecution jobExecution) {
        long totalRead = jobExecution.getStepExecutions().stream()
                .mapToLong(StepExecution::getReadCount)
                .sum();

        long totalWritten = jobExecution.getStepExecutions().stream()
                .mapToLong(StepExecution::getWriteCount)
                .sum();

        long totalSkips = jobExecution.getStepExecutions().stream()
                .mapToLong(StepExecution::getSkipCount)
                .sum();

        Map<String, String> writtenTickers = new LinkedHashMap<>();
        Map<String, Map<String, String>> skippedTickers = new HashMap<>();

        for (var stepExec : jobExecution.getStepExecutions()) {
            ExecutionContext ec = stepExec.getExecutionContext();

            // Collect written tickers into a direct ISIN -> Ticker map
            @SuppressWarnings("unchecked")
            List<Map<String, String>> stepWritten = (List<Map<String, String>>) ec.get("writtenTickersList");
            if (stepWritten != null) {
                for (Map<String, String> entry : stepWritten) {
                    writtenTickers.putAll(entry);
                }
            }

            // Collect skipped tickers grouped by reason into ISIN -> Ticker maps
            @SuppressWarnings("unchecked")
            Map<String, List<Map<String, String>>> stepSkipped =
                    (Map<String, List<Map<String, String>>>) ec.get("skippedTickersMap");
            if (stepSkipped != null) {
                stepSkipped.forEach((reason, list) -> {
                    Map<String, String> reasonMap = skippedTickers.computeIfAbsent(reason, k -> new LinkedHashMap<>());
                    for (Map<String, String> entry : list) {
                        reasonMap.putAll(entry);
                    }
                });
            }
        }

        String descriptiveStatus = switch (jobExecution.getStatus()) {
            case COMPLETED -> {
                if (totalWritten > 0 && totalSkips == 0) yield "COMPLETED";
                if (totalWritten > 0 && totalSkips > 0)  yield "COMPLETED_WITH_SKIPS";
                yield "FAILED"; // 0 written, 100% skipped
            }
            default -> jobExecution.getStatus().name();
        };

        return new BatchLoadResp(
                descriptiveStatus,
                totalRead,
                totalWritten,
                writtenTickers,
                totalSkips,
                skippedTickers
        );
    }

    public static BatchLoadResp mapToErrorResponse(String errorMessage) {
        return new BatchLoadResp(
                "FAILED",
                0,
                0,
                Map.of(),
                0,
                Map.of("Error", Map.of("System", errorMessage))
        );
    }
}