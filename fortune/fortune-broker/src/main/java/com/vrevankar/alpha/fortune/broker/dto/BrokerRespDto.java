package com.vrevankar.alpha.fortune.broker.dto;

import com.vrevankar.alpha.fortune.broker.entity.Broker;
import com.vrevankar.alpha.fortune.commons.dto.AddressResp;

import java.time.LocalDateTime;

public record BrokerRespDto(
        String dpId,
        String name,
        String brokerCd,
        String pan,
        String sebiRegnNo,
        AddressResp address,
        AddressResp secondaryAddress,
        String web,
        String active,
        String status,
        LocalDateTime crtDttm,
        LocalDateTime updtDttm
) {
    public static BrokerRespDto fromEntity(
            Broker broker,
            AddressResp primaryAddressDto,
            AddressResp secondaryAddressDto
    ) {
        return new BrokerRespDto(
                broker.getDpId(),
                broker.getName(),
                broker.getBrokerCd() != null ? broker.getBrokerCd().toUpperCase() : null,
                broker.getPan() != null ? broker.getPan().toUpperCase() : null,
                broker.getSebiRegnNo(),
                primaryAddressDto,
                secondaryAddressDto,
                broker.getWeb(),
                broker.getActive(),
                broker.getStatus(),
                broker.getCrtDttm(),
                broker.getUpdtDttm()
        );
    }
}