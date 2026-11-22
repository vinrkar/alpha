package com.vrevankar.alpha.fortune.market.service;


import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeMasterReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.ExchangeMasterResp;

import java.util.List;

public interface ExchangeMasterService {

    List<ExchangeMasterResp> onboardExchanges(List<ExchangeMasterReq> requests);

    ExchangeMasterResp patchExchange(Long xchgId, ExchangeMasterReq request);

    ExchangeMasterResp getExchangeById(Long xchgId);

    List<ExchangeMasterResp> getAllExchanges();

}