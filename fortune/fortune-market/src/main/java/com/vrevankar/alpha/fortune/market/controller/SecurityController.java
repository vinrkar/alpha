package com.vrevankar.alpha.fortune.market.controller;

import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;
import com.vrevankar.alpha.fortune.market.service.SecurityService;
import com.vrevankar.alpha.fortune.market.util.BatchResponseMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.*;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import static com.vrevankar.alpha.fortune.market.util.BatchResponseMapper.mapToResponse;

@Slf4j
@RestController
@RequestMapping("/api/v1/securities")
@RequiredArgsConstructor
@Tag(name = "Security Market Data", description = "Endpoints for batch loading and live data ingestion pipelines")
public class SecurityController {

    private final JobLauncher jobLauncher;
    private final Job securityJob;
    private final SecurityService securityService;

    @PostMapping("/load")
    @Operation(summary = "Load historic security data", description = "Triggers the batch job to extract historic pricing from SECURITY_MASTER and stream to Kafka.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Historic data load job completed with metrics"),
            @ApiResponse(responseCode = "500", description = "Job failed or failed to launch")
    })
    public ResponseEntity<BatchLoadResp> loadSecurities() {
        log.info("Received empty-body POST request to load historic security data.");

        try {
            JobParameters jobParameters = new JobParametersBuilder()
                    .addLong("time", System.currentTimeMillis())
                    .toJobParameters();

            JobExecution jobExecution = jobLauncher.run(securityJob, jobParameters);
            BatchLoadResp response = mapToResponse(jobExecution);

            if (jobExecution.getStatus() == BatchStatus.FAILED) {
                log.error("Batch job failed during execution. Status: {}", jobExecution.getStatus());
                return ResponseEntity.internalServerError().body(response);
            }

            HttpStatus httpStatus = switch (response.executionStatus()) {
                case "COMPLETED" -> HttpStatus.OK;                      // 200 OK
                case "COMPLETED_WITH_SKIPS" -> HttpStatus.MULTI_STATUS;  // 207 Multi-Status
                default -> HttpStatus.INTERNAL_SERVER_ERROR;
            };

            return ResponseEntity.status(httpStatus).body(response);
        } catch (Exception e) {
            log.error("Failed to start historic security enrichment job", e);
            return ResponseEntity.internalServerError().body(
                    BatchResponseMapper.mapToErrorResponse(e.getMessage())
            );
        }
    }

    @PostMapping("/live")
    @Operation(summary = "Trigger on-demand live data load", description = "Fetches live market data for all active securities from SECURITY_MASTER and streams to Kafka.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "On-demand live data load completed successfully"),
            @ApiResponse(responseCode = "207", description = "Completed with some skipped/failed securities"),
            @ApiResponse(responseCode = "500", description = "Pipeline execution failed")
    })
    public ResponseEntity<BatchLoadResp> triggerOnDemandLiveLoad() {
        log.info("Received POST request for on-demand live data load pipeline.");

        try {
            BatchLoadResp response = securityService.processOnDemandLiveLoad();

            if ("FAILED".equals(response.executionStatus())) {
                log.error("On-demand live load pipeline failed completely.");
                return ResponseEntity.internalServerError().body(response);
            }

            HttpStatus httpStatus = switch (response.executionStatus()) {
                case "COMPLETED" -> HttpStatus.OK;                      // 200 OK
                case "COMPLETED_WITH_SKIPS" -> HttpStatus.MULTI_STATUS;  // 207 Multi-Status
                default -> HttpStatus.INTERNAL_SERVER_ERROR;
            };

            return ResponseEntity.status(httpStatus).body(response);
        } catch (Exception e) {
            log.error("Failed to execute on-demand live data load pipeline", e);
            return ResponseEntity.internalServerError().body(
                    BatchResponseMapper.mapToErrorResponse(e.getMessage())
            );
        }
    }

}