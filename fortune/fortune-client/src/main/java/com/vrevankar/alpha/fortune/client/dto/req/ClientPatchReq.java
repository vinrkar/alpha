package com.vrevankar.alpha.fortune.client.dto.req;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.LocalDate;

public record ClientPatchReq(
        @Size(max = 30) String firstNm,
        @Size(max = 30) String lastNm,
        @Size(max = 20) String phNo,
        @Size(max = 60) String email,

        @Pattern(regexp = "^(NRO|NRE|RI)$", message = "accTyp must be NRO, NRE, or RI")
        String accTyp,

        @Pattern(regexp = "^(?i:Y|N|TRUE|FALSE)$", message = "pis must be Y, N, TRUE, or FALSE")
        String pis,

        LocalDate accCloseId
) {}