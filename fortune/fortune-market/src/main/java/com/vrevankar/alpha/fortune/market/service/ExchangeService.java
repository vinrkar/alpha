package com.vrevankar.alpha.fortune.market.service;

import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeBatchReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;

public interface ExchangeService {

    BatchLoadResp runHistoricBatch(ExchangeBatchReq request);

    void fetchAndPublishLiveRates();

}