package com.vrevankar.alpha.fortune.market.domain.dto.resp;

import java.util.Map;

public record BatchLoadResp(
        String executionStatus,
        long totalProcessed,
        long totalWritten,
        Map<String, String> writtenTickers, // Changed from List to Map for direct ISIN->Ticker key-values
        long totalSkipped,
        Map<String, Map<String, String>> skippedTickers // Grouped by reason, then ISIN->Ticker
) {}