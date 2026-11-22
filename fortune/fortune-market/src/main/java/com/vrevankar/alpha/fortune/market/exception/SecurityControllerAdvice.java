package com.vrevankar.alpha.fortune.market.exception;

import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@RestControllerAdvice
public class SecurityControllerAdvice {

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<BatchLoadResp> handleDuplicateKeyException(DataIntegrityViolationException ex) {
        log.error("Data integrity violation encountered during onboarding: {}", ex.getMessage());

        // Extract ISIN from message if present (e.g., 'INE985A01022')
        String isin = "UNKNOWN";
        Matcher matcher = Pattern.compile("ISIN:'([^']+)'").matcher(ex.getMessage());
        if (matcher.find()) {
            isin = matcher.group(1);
        }

        String errorMessage = String.format("Record with ISIN '%s' already exists", isin);

        BatchLoadResp response = new BatchLoadResp(
                "FAILED_DUPLICATE_ENTRY",
                0,
                0,
                Map.of(),
                1,
                Map.of("Constraint Violation", Map.of(isin, errorMessage))
        );

        return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
    }
}