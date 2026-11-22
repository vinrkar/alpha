package com.vrevankar.alpha.fortune.market.service;

import com.vrevankar.alpha.fortune.market.domain.dto.req.SecurityMasterPatchReq;
import com.vrevankar.alpha.fortune.market.domain.dto.req.SecurityMasterReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.SecurityMasterResp;
import com.vrevankar.alpha.fortune.market.domain.entity.SecurityMaster;

import java.util.List;

public interface SecurityMasterService {

    List<SecurityMasterResp> onboardSecurities(List<SecurityMasterReq> requests);
    
    SecurityMasterResp patchSecurity(String isin, SecurityMasterPatchReq request);
    
    SecurityMasterResp getSecurityByIsin(String isin);

    List<SecurityMasterResp> getAllSecurities();

    void processPendingRetries();

    void enrichAndUpsert(SecurityMaster security);

}