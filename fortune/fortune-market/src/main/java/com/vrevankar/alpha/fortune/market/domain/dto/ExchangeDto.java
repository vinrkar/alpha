package com.vrevankar.alpha.fortune.market.domain.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.LocalDate;

public record ExchangeDto(
        @JsonProperty("from_curr")
        String frCurr,

        @JsonProperty("to_curr")
        String toCurr,

        @JsonProperty("xchg_dt")
        @JsonFormat(pattern = "yyyy-MM-dd")
        LocalDate xchgDt,

        @JsonProperty("xchg_rt")
        BigDecimal xchgRt
) {}