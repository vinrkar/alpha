package com.vrevankar.alpha.fortune.client.dto.req;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ClientIdentityReq(
        @NotBlank @Size(max = 30) String idTyp,
        @NotBlank @Size(max = 20) String idVal
) {}