package com.vrevankar.alpha.fortune.market.service;

import com.vrevankar.alpha.fortune.market.domain.dto.resp.BatchLoadResp;

public interface SecurityService {

    BatchLoadResp processOnDemandLiveLoad();

}
