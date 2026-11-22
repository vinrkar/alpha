package com.vrevankar.alpha.fortune.market.controller;

import com.vrevankar.alpha.fortune.market.common.validation.OnCreate;
import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeMasterBatchReq;
import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeMasterReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.ExchangeMasterResp;
import com.vrevankar.alpha.fortune.market.service.ExchangeMasterService;
import com.vrevankar.alpha.fortune.market.util.BatchResponseUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Validated
@RestController
@RequestMapping("/api/v1/exchange")
@RequiredArgsConstructor
@Tag(name = "Exchange Master", description = "Endpoints for managing currency pairs and exchange reference data")
public class ExchangeMasterController {

    private final ExchangeMasterService exchangeMasterService;

    @PostMapping("/onboard")
    @Operation(summary = "Onboard exchange currency pairs", description = "Batch registers or updates currency pairs in the master database.")
    @ApiResponses({
            @ApiResponse(responseCode = "201", description = "Currency pairs successfully onboarded"),
            @ApiResponse(responseCode = "207", description = "Currency pairs partially onboarded (Multi-Status)"),
            @ApiResponse(responseCode = "400", description = "Invalid request payload or validation failed")
    })
    public ResponseEntity<List<ExchangeMasterResp>> onboardExchanges(
            @Validated(OnCreate.class) @RequestBody ExchangeMasterBatchReq batchReq) {

        List<ExchangeMasterResp> responses = exchangeMasterService.onboardExchanges(batchReq.exchanges());

        HttpStatus responseStatus = BatchResponseUtil.resolveBatchStatus(responses);

        return ResponseEntity.status(responseStatus).body(responses);
    }

    @PatchMapping("/{xchgId}")
    @Operation(summary = "Patch exchange pair status", description = "Updates status attributes for a specific currency pair ID.")
    public ResponseEntity<ExchangeMasterResp> patchExchange(
            @PathVariable Long xchgId,
            @RequestBody @Valid ExchangeMasterReq request) {
        return ResponseEntity.ok(exchangeMasterService.patchExchange(xchgId, request));
    }

    @GetMapping("/{xchgId}")
    @Operation(summary = "Get exchange pair by ID", description = "Retrieves reference data for a specific currency pair using its surrogate ID.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Exchange pair found"),
            @ApiResponse(responseCode = "404", description = "Exchange pair not found")
    })
    public ResponseEntity<ExchangeMasterResp> getExchangeById(@PathVariable Long xchgId) {
        return ResponseEntity.ok(exchangeMasterService.getExchangeById(xchgId));
    }

    @GetMapping
    @Operation(summary = "Get all exchange pairs", description = "Retrieves a list of all currency pairs configured in the master database.")
    @ApiResponse(responseCode = "200", description = "Successfully retrieved list of currency pairs")
    public ResponseEntity<List<ExchangeMasterResp>> getAllExchanges() {
        return ResponseEntity.ok(exchangeMasterService.getAllExchanges());
    }
}