package com.vrevankar.alpha.fortune.market.domain.dto.req;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import java.time.LocalDate;

public record SecurityMasterReq(
        @NotBlank
        @Pattern(regexp = "^[A-Z0-9]{12}$", message = "Invalid ISIN format")
        String isin,

        @NotNull
        LocalDate startDt
) {}