package com.vrevankar.alpha.fortune.client.helper;

import com.vrevankar.alpha.fortune.client.entity.IdType;
import com.vrevankar.alpha.fortune.client.repository.IdTypeRepo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.regex.Pattern;

@Slf4j
@Component
@RequiredArgsConstructor
public class IdTypeValidationHelper {

    private final IdTypeRepo idTypeRepo;

    public String validateAndNormalizeAndEnforceRegex(String idTyp, String idVal) {
        if (idVal == null) {
            throw new IllegalArgumentException("Identity value cannot be null.");
        }

        // 1. Normalize input to uppercase for case-insensitive UX
        String normalizedVal = idVal.trim().toUpperCase();
        log.debug("Validating identity type: {} with normalized value: {}", idTyp, normalizedVal);

        IdType idTypeConfig = idTypeRepo.findById(idTyp)
                .orElseThrow(() -> new IllegalArgumentException("Unsupported or unknown identity type: '" + idTyp + "'"));

        if (!"Y".equalsIgnoreCase(idTypeConfig.getActive())) {
            throw new IllegalArgumentException("Identity type '" + idTyp + "' is currently inactive.");
        }

        String regex = idTypeConfig.getRegex();
        if (regex != null && !regex.isBlank()) {
            if (!Pattern.matches(regex, normalizedVal)) {
                throw new IllegalArgumentException(String.format(
                        "Invalid value '%s' for identity type '%s'. It does not match the required pattern: %s",
                        idVal, idTyp, regex
                ));
            }
        }

        return normalizedVal; // Return the clean uppercase version to be saved
    }
}