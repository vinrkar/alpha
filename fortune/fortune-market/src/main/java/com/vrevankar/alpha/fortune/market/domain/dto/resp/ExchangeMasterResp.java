package com.vrevankar.alpha.fortune.market.domain.dto.resp;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.LocalDateTime;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ExchangeMasterResp(
        Long xchgId,
        String frCurr,
        String toCurr,
        String active,

        @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
        LocalDateTime crtDttm,

        @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
        LocalDateTime updtDttm,

        String status
) {}