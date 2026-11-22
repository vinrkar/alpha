package com.vrevankar.alpha.fortune.market.domain.dto.req;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import java.util.List;

public record ExchangeMasterBatchReq(
        @NotEmpty(message = "Exchange batch request list cannot be empty")
        @Valid
        List<ExchangeMasterReq> exchanges
) {}