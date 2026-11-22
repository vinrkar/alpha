package com.vrevankar.alpha.fortune.commons.dto;

public record BrokerStatusResp(
        String  dpId,
        String status,
        boolean active
) {}