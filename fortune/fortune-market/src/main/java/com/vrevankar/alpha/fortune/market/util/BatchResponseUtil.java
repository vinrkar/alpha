package com.vrevankar.alpha.fortune.market.util;

import com.vrevankar.alpha.fortune.market.domain.dto.resp.ExchangeMasterResp;
import lombok.AccessLevel;
import lombok.NoArgsConstructor;
import org.springframework.http.HttpStatus;

import java.util.List;

@NoArgsConstructor(access = AccessLevel.PRIVATE)
public final class BatchResponseUtil {

    public static HttpStatus resolveBatchStatus(List<ExchangeMasterResp> responses) {
        if (responses == null || responses.isEmpty()) {
            return HttpStatus.INTERNAL_SERVER_ERROR;
        }

        long completedCount = responses.stream()
                .filter(r -> "COMPLETED".equalsIgnoreCase(r.status()))
                .count();

        return completedCount == responses.size() ?
                HttpStatus.CREATED : completedCount > 0 ?
                    HttpStatus.MULTI_STATUS : HttpStatus.INTERNAL_SERVER_ERROR;
    }
}