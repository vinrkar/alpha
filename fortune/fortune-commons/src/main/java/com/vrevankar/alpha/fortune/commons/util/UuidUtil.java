package com.vrevankar.alpha.fortune.commons.util;

import lombok.AccessLevel;
import lombok.NoArgsConstructor;

import java.util.UUID;

@NoArgsConstructor(access = AccessLevel.PRIVATE)
public final class UuidUtil {

    public static UUID parseUuidSafely(String input) {
        if (input == null || input.isBlank()) {
            throw new IllegalArgumentException("Client ID cannot be null or blank.");
        }

        try {
            // Handle 32-character hex strings without hyphens (e.g. from raw DB inputs)
            if (input.length() == 32 && !input.contains("-")) {
                String formatted = String.format("%s-%s-%s-%s-%s",
                        input.substring(0, 8),
                        input.substring(8, 12),
                        input.substring(12, 16),
                        input.substring(16, 20),
                        input.substring(20, 32));
                return UUID.fromString(formatted);
            }
            return UUID.fromString(input);
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid UUID format: '" + input + "'", e);
        }
    }
}