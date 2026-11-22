package com.vrevankar.alpha.fortune.market.domain.dto.req;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDate;

public record ExchangeBatchReq(
        @JsonProperty("start_dt")
        @JsonFormat(pattern = "yyyy-MM-dd")
        LocalDate startDt,

        @JsonProperty("end_dt")
        @JsonFormat(pattern = "yyyy-MM-dd")
        LocalDate endDt
) {}