package com.vrevankar.alpha.fortune.broker.service;

import com.vrevankar.alpha.fortune.broker.dto.BrokerReqDto;
import com.vrevankar.alpha.fortune.broker.dto.BrokerRespDto;
import com.vrevankar.alpha.fortune.commons.dto.BrokerStatusResp;

import java.util.List;

public interface BrokerService {

    BrokerRespDto createBroker(BrokerReqDto reqDto);

    List<BrokerRespDto> getAllBrokers();

    BrokerRespDto getBrokerById(Long dpId);

    void deleteBroker(Long dpId);

    BrokerStatusResp getBrokerStatus(Long dpId);

}