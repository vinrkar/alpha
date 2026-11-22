package com.vrevankar.alpha.fortune.market.controller;

import com.vrevankar.alpha.fortune.market.domain.dto.req.SecurityMasterPatchReq;
import com.vrevankar.alpha.fortune.market.domain.dto.req.SecurityMasterReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.SecurityMasterResp;
import com.vrevankar.alpha.fortune.market.service.SecurityMasterService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

import static org.springframework.http.HttpStatus.*;

@Validated
@RestController
@RequestMapping("/api/v1/securities")
@RequiredArgsConstructor
@Tag(name = "Security Master", description = "Endpoints for onboarding and managing financial securities and reference data")
public class SecurityMasterController {

    // Depend on the interface, not the Impl class
    private final SecurityMasterService securityMasterService;

    @PostMapping("/onboard")
    @Operation(summary = "Onboard securities", description = "Batch registers or updates financial securities in the system.")
    @ApiResponses({
            @ApiResponse(responseCode = "201", description = "Securities successfully onboarded"),
            @ApiResponse(responseCode = "400", description = "Invalid request payload or validation failed")
    })
    public ResponseEntity<List<SecurityMasterResp>> onboardSecurities(
            @Valid @RequestBody List<SecurityMasterReq> requests) {

        List<SecurityMasterResp> responses = securityMasterService.onboardSecurities(requests);
        long completedCount = responses.stream()
                .filter(r -> "COMPLETED".equalsIgnoreCase(r.status()))
                .count();
        return ResponseEntity.status(
                        completedCount == responses.size() ? CREATED : completedCount > 0 ? MULTI_STATUS : INTERNAL_SERVER_ERROR)
                .body(responses);
    }

    @PatchMapping("/{isin}")
    public ResponseEntity<SecurityMasterResp> patchSecurity(
            @PathVariable @Pattern(regexp = "^[A-Z0-9]{12}$") String isin,
            @RequestBody @Valid SecurityMasterPatchReq request) {
        SecurityMasterResp response = securityMasterService.patchSecurity(isin, request);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{isin}")
    @Operation(summary = "Get security by ISIN", description = "Retrieves detailed reference data for a specific security using its ISIN.")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Security found"),
            @ApiResponse(responseCode = "404", description = "Security not found for the given ISIN")
    })
    public ResponseEntity<SecurityMasterResp> getSecurityByIsin(@PathVariable String isin) {
        return ResponseEntity.ok(securityMasterService.getSecurityByIsin(isin));
    }

    @GetMapping
    @Operation(summary = "Get all securities", description = "Retrieves a list of all active securities in the master database.")
    @ApiResponse(responseCode = "200", description = "Successfully retrieved list of securities")
    public ResponseEntity<List<SecurityMasterResp>> getAllSecurities() {
        return ResponseEntity.ok(securityMasterService.getAllSecurities());
    }
}