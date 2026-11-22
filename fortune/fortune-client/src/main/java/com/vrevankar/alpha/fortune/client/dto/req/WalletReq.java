package com.vrevankar.alpha.fortune.client.dto.req;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

public record WalletReq(
        @Size(max = 3) String curr,
        @NotBlank @Size(max = 30) String bankNm,
        @NotBlank @Pattern(regexp = "^(SAVINGS|PIS)$") String accTyp,
        @NotBlank @Size(max = 14) String accNo,
        BigDecimal balAmt,
        BigDecimal blockedAmt
) {}