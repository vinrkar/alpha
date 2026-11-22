package com.vrevankar.alpha.fortune.commons.exception;

import com.vrevankar.alpha.fortune.commons.dto.ErrorResp;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingPathVariableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.time.Instant;
import java.util.stream.Collectors;

@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResp> handleMessageNotReadable(HttpMessageNotReadableException ex, HttpServletRequest request) {
        String errorMessage = "Malformed JSON request or invalid data type provided.";

        Throwable cause = ex.getCause();
        if (cause instanceof com.fasterxml.jackson.databind.exc.InvalidFormatException ife) {
            String fieldName = ife.getPath().stream()
                    .map(com.fasterxml.jackson.databind.JsonMappingException.Reference::getFieldName)
                    .filter(java.util.Objects::nonNull)
                    .collect(Collectors.joining("."));

            String targetType = ife.getTargetType().getSimpleName();
            errorMessage = String.format("Invalid value '%s' for field '%s'. Expected type: %s.",
                    ife.getValue(), fieldName, targetType);
        } else if (cause instanceof com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException upe) {
            errorMessage = String.format("Unrecognized field '%s' is not allowed in the request payload.",
                    upe.getPropertyName());
        }

        log.warn("JSON parsing error at path {}: {}", request.getRequestURI(), errorMessage);

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                errorMessage,
                request.getRequestURI()
        );
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ErrorResp> handleIllegalArgument(IllegalArgumentException ex, HttpServletRequest request) {
        log.warn("Business validation error: {}", ex.getMessage());

        HttpStatus status = ex.getMessage().contains("not found") ? HttpStatus.NOT_FOUND : HttpStatus.BAD_REQUEST;

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                status.value(),
                status.getReasonPhrase(),
                ex.getMessage(),
                request.getRequestURI()
        );
        return ResponseEntity.status(status).body(error);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResp> handleValidationExceptions(MethodArgumentNotValidException ex, HttpServletRequest request) {
        String errorMessage = ex.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));

        log.warn("Payload validation failed: {}", errorMessage);

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                errorMessage,
                request.getRequestURI()
        );
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    @ExceptionHandler(MissingPathVariableException.class)
    public ResponseEntity<ErrorResp> handleMissingPathVariable(MissingPathVariableException ex, HttpServletRequest request) {
        log.warn("Missing path variable at path {}: {}", request.getRequestURI(), ex.getMessage());

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                "Required path variable '" + ex.getVariableName() + "' is missing in the URL.",
                request.getRequestURI()
        );
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ErrorResp> handleMethodNotSupported(HttpRequestMethodNotSupportedException ex, HttpServletRequest request) {
        log.warn("Method not supported at path {}: {}", request.getRequestURI(), ex.getMessage());

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                HttpStatus.METHOD_NOT_ALLOWED.value(),
                HttpStatus.METHOD_NOT_ALLOWED.getReasonPhrase(),
                ex.getMessage(),
                request.getRequestURI()
        );
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED).body(error);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResp> handleGlobalException(Exception ex, HttpServletRequest request) {
        log.error("Unexpected error occurred at path {}: ", request.getRequestURI(), ex);

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                HttpStatus.INTERNAL_SERVER_ERROR.value(),
                HttpStatus.INTERNAL_SERVER_ERROR.getReasonPhrase(),
                "An unexpected internal server error occurred.",
                request.getRequestURI()
        );
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResp> handleTypeMismatch(MethodArgumentTypeMismatchException ex, HttpServletRequest request) {
        String paramName = ex.getName();
        String invalidValue = ex.getValue() != null ? ex.getValue().toString() : "null";
        String requiredType = ex.getRequiredType() != null ? ex.getRequiredType().getSimpleName() : "unknown";

        String errorMessage = String.format("Parameter '%s' has an invalid value '%s'. Expected type: %s.",
                paramName, invalidValue, requiredType);

        log.warn("Type mismatch error at path {}: {}", request.getRequestURI(), errorMessage);

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                errorMessage,
                request.getRequestURI()
        );
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<ErrorResp> handleDataIntegrityViolation(DataIntegrityViolationException ex, HttpServletRequest request) {
        String errorMessage = "Database constraint violation. Please verify your input data.";

        Throwable rootCause = ex.getRootCause();
        if (rootCause != null && rootCause.getMessage() != null) {
            String causeMsg = rootCause.getMessage();

            if (causeMsg.contains("ORA-00001")) {
                // Extract constraint name if present (e.g., unique constraint (USER.UK_NAME) violated)
                if (causeMsg.contains("unique constraint")) {
                    errorMessage = "Duplicate key violation: A record with this unique value already exists in the system.";
                    // Optional: Make it ultra-specific based on your constraint names
                    if (causeMsg.contains("UK__WALLET__CLIENT_ID__BANK_NM_SVNG_ACC_NO")) {
                        errorMessage = "A wallet with this bank name and savings account number already exists.";
                    } else if (causeMsg.contains("UK__WALLET__CLIENT_ID__BANK_NM_PIS_ACC_NO")) {
                        errorMessage = "A wallet with this bank name and PIS account number already exists.";
                    } else if (causeMsg.contains("UK__WALLET")) {
                        errorMessage = "A wallet with this bank name and account details already exists.";
                    } else if (causeMsg.contains("CLIENT")) {
                        errorMessage = "Duplicate entry: A client with this unique identifier (such as email, phone, or identity) already exists.";
                    }
                } else {
                    errorMessage = "Duplicate key violation: A record with this unique identifier already exists.";
                }
            } else if (causeMsg.contains("ORA-02291")) {
                errorMessage = "Invalid reference: The provided master data value (such as ID type or DP ID) does not exist.";
            } else if (causeMsg.contains("ORA-02290")) {
                errorMessage = "Check constraint violation: One or more field values do not meet allowed business rules.";
            }
        }

        log.warn("Data integrity violation at path {}: {}", request.getRequestURI(), ex.getMessage());

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                errorMessage,
                request.getRequestURI()
        );
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    @ExceptionHandler(org.springframework.web.client.ResourceAccessException.class)
    public ResponseEntity<ErrorResp> handleResourceAccessException(
            org.springframework.web.client.ResourceAccessException ex, HttpServletRequest request) {

        log.error("Downstream service communication failure at path {}: {}", request.getRequestURI(), ex.getMessage());

        ErrorResp error = new ErrorResp(
                Instant.now().toString(),
                HttpStatus.SERVICE_UNAVAILABLE.value(),
                HttpStatus.SERVICE_UNAVAILABLE.getReasonPhrase(),
                "Unable to communicate with required downstream services. Please try again later.",
                request.getRequestURI()
        );
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(error);
    }

}