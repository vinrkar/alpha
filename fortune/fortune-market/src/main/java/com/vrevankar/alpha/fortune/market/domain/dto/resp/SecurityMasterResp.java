package com.vrevankar.alpha.fortune.market.domain.dto.resp;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

public record SecurityMasterResp(
        UUID secId,
        String isin,
        String ticker,
        String secNm,
        String xchg,
        String curr,
        Boolean active,
        LocalDate startDt,
        String status,
        LocalDateTime crtDttm,
        LocalDateTime updtDttm
) {}