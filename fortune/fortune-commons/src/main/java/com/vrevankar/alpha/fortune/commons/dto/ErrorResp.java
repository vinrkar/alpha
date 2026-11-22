package com.vrevankar.alpha.fortune.commons.dto;

public record ErrorResp(
        String timestamp,
        int status,
        String error,
        String message,
        String path
) {}