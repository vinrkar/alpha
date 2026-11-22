package com.vrevankar.alpha.fortune.broker.dto;

import com.vrevankar.alpha.fortune.commons.dto.AddressReq;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record BrokerReqDto(

        @NotBlank(message="DP ID is required")
        @Size(max=8, message="DP ID cannot exceed 8 characters")
        String dpId,

        @NotBlank(message = "Broker name is required")
        @Size(max=60, message="Broker name cannot exceed 60 characters")
        String name,

        @NotBlank(message="Broker code is required")
        @Size(max=7, message="Broker code cannot exceed 7 characters")
        String brokerCd,

        @NotBlank(message="PAN is required")
        @Size(max=10, message="PAN cannot exceed 10 characters")
        String pan,

        @NotBlank(message="SEBI registration number is required")
        @Size(max=12, message="SEBI registration number cannot exceed 12 characters")
        String sebiRegnNo,

        @NotNull(message="Primary address is required")
        @Valid
        AddressReq primaryAddress,

        @NotNull(message="Secondary address is required")
        @Valid
        AddressReq secondaryAddress,

        @NotBlank(message="Website URL is required")
        String web,

        String active,
        String status
) {}