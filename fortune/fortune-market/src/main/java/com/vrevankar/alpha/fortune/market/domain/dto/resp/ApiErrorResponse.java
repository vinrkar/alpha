package com.vrevankar.alpha.fortune.market.domain.dto.resp;

import java.time.LocalDateTime;
import java.util.Map;

public record ApiErrorResponse(
        LocalDateTime timestamp,
        int status,
        String error,
        String message,
        Map<String, String> validationErrors,
        String path
) {}