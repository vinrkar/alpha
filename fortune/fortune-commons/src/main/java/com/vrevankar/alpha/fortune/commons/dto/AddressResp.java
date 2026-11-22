package com.vrevankar.alpha.fortune.commons.dto;

import com.vrevankar.alpha.fortune.commons.entity.Address;

public record AddressResp(
        String addrId,
        String street,
        String city,
        String pin,
        String isoCd,
        String state,     // Can be null during initial onboarding
        String country,   // Can be null during initial onboarding
        String phNo,
        String email,
        String status
) {
    // 1. Overloaded method for simple mapping (e.g., Client Onboarding)
    public static AddressResp fromEntity(Address entity) {
        return fromEntity(entity, null, null);
    }

    // 2. Full method for enriched batch validation (e.g., Nominatim / AddressValScheduler)
    public static AddressResp fromEntity(Address entity, String state, String country) {
        return new AddressResp(
                entity.getAddrId() != null ? entity.getAddrId().toString().toUpperCase() : null,
                entity.getStreet(),
                entity.getCity(),
                entity.getPin(),
                entity.getIsoCd() != null ? entity.getIsoCd().toUpperCase() : null,
                state,
                country,
                entity.getPhNo(),
                entity.getEmail() != null ? entity.getEmail().toLowerCase() : null,
                entity.getStatus() != null ? entity.getStatus().name() : null
        );
    }
}