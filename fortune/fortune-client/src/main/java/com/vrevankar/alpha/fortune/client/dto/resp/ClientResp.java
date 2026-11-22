package com.vrevankar.alpha.fortune.client.dto.resp;

import com.vrevankar.alpha.fortune.commons.dto.AddressResp;

import java.time.LocalDate;
import java.util.List;

public record ClientResp(
        String clientId,
        String dpId,
        String clientCd,
        String tradeCd,
        String firstNm,
        String lastNm,
        String phNo,
        String email,
        String password,
        String accTyp,
        String pis,
        LocalDate accOpenDt,
        LocalDate accCloseDt,
        AddressResp address,
        List<ClientIdentityResp> identities,
        List<WalletResp> wallets
) {
    public static ClientResp fromEntity(com.vrevankar.alpha.fortune.client.entity.Client e) {
        return new ClientResp(
                e.getClientId() != null ? e.getClientId().toString().toUpperCase() : null,
                e.getDpId(),
                e.getClientCd(),
                e.getTradeCd(),
                e.getFirstNm(),
                e.getLastNm(),
                e.getPhNo(),
                e.getEmail(),
                e.getPassword(),
                e.getAccTyp(),
                (e.getPis() != null && e.getPis()) ? "Y" : "N",
                e.getAccOpenDt(),
                e.getAccCloseDt(),
                e.getAddress() != null ? AddressResp.fromEntity(e.getAddress()) : null,
                e.getIdentities() != null ? e.getIdentities().stream().map(ClientIdentityResp::fromEntity).toList() : List.of(),
                e.getWallets() != null ? e.getWallets().stream().map(WalletResp::fromEntity).toList() : List.of()
        );
    }
}