package com.vrevankar.alpha.fortune.client.validation;

import com.vrevankar.alpha.fortune.client.adapter.BrokerAdapter;
import com.vrevankar.alpha.fortune.client.dto.req.ClientReq;
import com.vrevankar.alpha.fortune.client.dto.req.WalletReq;
import com.vrevankar.alpha.fortune.client.repository.ClientRepo;
import com.vrevankar.alpha.fortune.client.repository.IdTypeRepo;
import com.vrevankar.alpha.fortune.commons.converter.YesNoBooleanConverter;
import com.vrevankar.alpha.fortune.commons.util.PhNoUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class ClientValidator {

    private final IdTypeRepo idTypeRepo;
    private final ClientRepo clientRepo;
    private final BrokerAdapter brokerAdapter;

    public void validateClientOnboarding(ClientReq req) {
        // 1. Validate Broker exists and is active
        brokerAdapter.validateBrokerActive(req.dpId());

        // 2. Client Code Uniqueness per DP
        if (clientRepo.existsByDpIdAndClientCd(req.dpId(), req.clientCd())) {
            throw new IllegalArgumentException("Client code '" + req.clientCd() + "' already exists for DP ID " + req.dpId());
        }

        // 3. Trade Code Uniqueness per DP (Trading portal login ID must be globally unique per broker)
        if (clientRepo.existsByDpIdAndTradeCd(req.dpId(), req.tradeCd())) {
            throw new IllegalArgumentException("Trade code / login ID '" + req.tradeCd() + "' is already in use for DP ID " + req.dpId());
        }

        // 4. Phone Country Code Matching (Using shared library utility)
        PhNoUtil.validatePhoneCountryMatch(req.address().isoCd(), req.address().phNo());

        // 5. Account Type vs Non-Indian Address Validation
        validateAccountTypeAndAddress(req.address().isoCd(), req.accTyp().name());

        // 6. Mandatory Wallets & Bank Consistency when PIS is enabled
        if (YesNoBooleanConverter.parse(req.pis())) {
            long distinctBanks = req.wallets().stream()
                    .map(WalletReq::bankNm)
                    .distinct()
                    .count();
            if (distinctBanks > 1) {
                throw new IllegalArgumentException("For PIS accounts, both savings and PIS wallets must belong to the same bank.");
            }

            boolean hasSavings = req.wallets().stream().anyMatch(w -> "SAVINGS".equalsIgnoreCase(w.accTyp()));
            boolean hasPis = req.wallets().stream().anyMatch(w -> "PIS".equalsIgnoreCase(w.accTyp()));
            if (!hasSavings || !hasPis) {
                throw new IllegalArgumentException("Clients with PIS enabled must provide both a SAVINGS and a PIS wallet account.");
            }
        }

        req.identities().forEach(idReq -> {
            if (!idTypeRepo.existsById(idReq.idTyp())) {
                throw new IllegalArgumentException(
                        String.format("Invalid reference: The provided master data value (such as ID type, %s) does not exist.",
                                idReq.idTyp())
                );
            }
        });
    }

    private void validateAccountTypeAndAddress(String isoCd, String accTyp) {
        boolean isIndianAddress = isoCd.toUpperCase().startsWith("IN");
        if (!isIndianAddress && !"PIS".equalsIgnoreCase(accTyp)) {
            throw new IllegalArgumentException("Non-Indian addresses require account type to be PIS.");
        }
    }

    private boolean parseBooleanFlag(String val) {
        if (val == null) return false;
        String trimmed = val.trim();
        return "Y".equalsIgnoreCase(trimmed) || "TRUE".equalsIgnoreCase(trimmed);
    }
}