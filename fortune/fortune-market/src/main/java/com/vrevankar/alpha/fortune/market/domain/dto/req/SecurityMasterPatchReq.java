package com.vrevankar.alpha.fortune.market.domain.dto.req;

import java.time.LocalDate;

public record SecurityMasterPatchReq(
        Boolean active,
        LocalDate endDt
) {}