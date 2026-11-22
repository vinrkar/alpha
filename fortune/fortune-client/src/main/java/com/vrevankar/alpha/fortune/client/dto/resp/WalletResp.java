package com.vrevankar.alpha.fortune.client.dto.resp;

import com.vrevankar.alpha.fortune.client.entity.Wallet;

import java.math.BigDecimal;

public record WalletResp(
        String walletId,
        String clientId,
        String curr,
        String bankNm,
        String accTyp,
        String accNo,
        BigDecimal balAmt,
        BigDecimal blockedAmt
) {
    public static WalletResp fromEntity(Wallet e) {
        return new WalletResp(
                e.getWalletId() != null ? e.getWalletId().toString().toUpperCase() : null,
                (e.getClient() != null && e.getClient().getClientId() != null)
                        ? e.getClient().getClientId().toString().toUpperCase()
                        : null,
                e.getCurr(),
                e.getBankNm(),
                e.getAccTyp(),
                e.getAccNo(),
                e.getBalAmt(),
                e.getBlockedAmt()
        );
    }
}