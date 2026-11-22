package com.vrevankar.alpha.fortune.market.domain.dto.req;

import com.vrevankar.alpha.fortune.market.common.validation.OnCreate;
import com.vrevankar.alpha.fortune.market.common.validation.ValidCurrency;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

public record ExchangeMasterReq(

        @NotNull(groups = OnCreate.class, message = "From currency cannot be null")
        @ValidCurrency(message = "From currency must be a valid ISO 4217 code")
        @Pattern(regexp = "^[A-Z]{3}$", message = "From currency must be a valid 3-letter ISO code")
        String frCurr,

        @NotNull(groups = OnCreate.class, message = "To currency cannot be null")
        @ValidCurrency(message = "To currency must be a valid ISO 4217 code")
        @Pattern(regexp = "^[A-Z]{3}$", message = "To currency must be a valid 3-letter ISO code")
        String toCurr,

        @Pattern(regexp = "^[YN]$", message = "Active status must be 'Y' or 'N'")
        String active

) {}