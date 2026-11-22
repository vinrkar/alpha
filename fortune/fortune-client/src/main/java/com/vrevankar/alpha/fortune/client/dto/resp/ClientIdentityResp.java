package com.vrevankar.alpha.fortune.client.dto.resp;

public record ClientIdentityResp(
        String clientId,
        String idTyp,
        String idVal
) {
    public static ClientIdentityResp fromEntity(com.vrevankar.alpha.fortune.client.entity.ClientIdentity e) {
        return new ClientIdentityResp(
                e.getClientId() != null ? e.getClientId().toString().toUpperCase() : null,
                e.getIdTyp(),
                e.getIdVal()
        );
    }
}