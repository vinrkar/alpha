package com.vrevankar.alpha.fortune.client.service.impl;

import com.vrevankar.alpha.fortune.client.dto.req.ClientPatchReq;
import com.vrevankar.alpha.fortune.client.dto.req.ClientReq;
import com.vrevankar.alpha.fortune.client.dto.resp.ClientResp;
import com.vrevankar.alpha.fortune.client.entity.Client;
import com.vrevankar.alpha.fortune.client.entity.ClientIdentity;
import com.vrevankar.alpha.fortune.client.entity.Wallet;
import com.vrevankar.alpha.fortune.client.enums.AccountType;
import com.vrevankar.alpha.fortune.client.repository.ClientRepo;
import com.vrevankar.alpha.fortune.client.service.ClientService;
import com.vrevankar.alpha.fortune.client.validation.ClientValidator;
import com.vrevankar.alpha.fortune.commons.converter.YesNoBooleanConverter;
import com.vrevankar.alpha.fortune.commons.entity.Address;
import com.vrevankar.alpha.fortune.commons.service.EmailService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.jasypt.encryption.StringEncryptor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class ClientServiceImpl implements ClientService {

    private final ClientRepo clientRepo;
    private final ClientValidator clientValidator;
    private final StringEncryptor stringEncryptor;
    private final EmailService emailService;

    @Override
    @Transactional
    public ClientResp onboardClient(ClientReq req) {
        log.info("Onboarding new client with code: {}", req.clientCd());

        clientValidator.validateClientOnboarding(req);

        Address address = Address.builder()
                .street(req.address().street())
                .city(req.address().city())
                .pin(req.address().pin())
                .isoCd(req.address().isoCd())
                .phNo(req.address().phNo())
                .email(req.address().email())
                .build();

        // Encrypt the plain-text password using Jasypt
        String encryptedPassword = stringEncryptor.encrypt(req.password());

        Client client = Client.builder()
                .dpId(req.dpId())
                .clientCd(req.clientCd())
                .tradeCd(req.tradeCd())
                .firstNm(req.firstNm())
                .lastNm(req.lastNm())
                .phNo(req.phNo())
                .email(req.email())
                .password(encryptedPassword)
                .accTyp(req.accTyp() != null ? req.accTyp().name() : AccountType.NRO.name())
                .pis(YesNoBooleanConverter.parse(req.pis()))
                .accOpenDt(req.accOpenDt())
                .accCloseDt(req.accCloseDt())
                .address(address)
                .build();

        req.identities().forEach(idReq -> {
            ClientIdentity identity = ClientIdentity.builder()
                    .idTyp(idReq.idTyp())
                    .idVal(idReq.idVal())
                    .build();
            client.addIdentity(identity);
        });

        req.wallets().forEach(wReq -> {
            Wallet wallet = Wallet.builder()
                    .curr(wReq.curr() != null ? wReq.curr() : "INR")
                    .bankNm(wReq.bankNm())
                    .accTyp(wReq.accTyp())
                    .accNo(wReq.accNo())
                    .balAmt(wReq.balAmt() != null ? wReq.balAmt() : BigDecimal.ZERO)
                    .blockedAmt(wReq.blockedAmt() != null ? wReq.blockedAmt() : BigDecimal.ZERO)
                    .build();
            client.addWallet(wallet);
        });

        // 1. Single database save containing client, address, identities, and wallets
        Client savedClient = clientRepo.save(client);
        log.info("Successfully persisted client onboarding record with ID: {}", savedClient.getClientId());

        String subject = "Welcome to Alpha - Your Account Credentials";
        String body = String.format(
                "Dear %s,<br><br>" +
                        "Your onboarding process has been successfully completed.<br>" +
                        "Your temporary password is: <b>%s</b><br><br>" +
                        "Please update your password upon your first login.<br><br>" +
                        "Regards,<br>Alpha Platform Team",
                req.firstNm(), req.password()
        );
        emailService.sendEmailAsync(req.email(), subject, body);

        return ClientResp.fromEntity(savedClient);
    }

    @Override
    @Transactional(readOnly = true)
    public List<ClientResp> getAllClients() {
        log.debug("Fetching all clients");
        return clientRepo.findAll().stream()
                .map(ClientResp::fromEntity)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public ClientResp getClientById(UUID clientId) {
        log.debug("Fetching client by ID: {}", clientId);
        Client client = clientRepo.findById(clientId)
                .orElseThrow(() -> new IllegalArgumentException("Client not found with ID: " + clientId));
        return ClientResp.fromEntity(client);
    }

    @Override
    @Transactional
    public ClientResp patchClient(UUID clientId, ClientPatchReq req) {
        log.info("Patching client with ID: {}", clientId);
        Client client = clientRepo.findById(clientId)
                .orElseThrow(() -> new IllegalArgumentException("Client not found with ID: " + clientId));

        if (req.firstNm() != null) client.setFirstNm(req.firstNm());
        if (req.lastNm() != null) client.setLastNm(req.lastNm());
        if (req.phNo() != null) client.setPhNo(req.phNo());
        if (req.email() != null) client.setEmail(req.email());
        if (req.accTyp() != null) client.setAccTyp(req.accTyp());
        if (req.pis() != null) client.setPis(YesNoBooleanConverter.parse(req.pis()));
        if (req.accCloseId() != null) client.setAccCloseDt(req.accCloseId());

        Client updatedClient = clientRepo.save(client);
        return ClientResp.fromEntity(updatedClient);
    }

    @Override
    @Transactional
    public void deleteClient(UUID clientId) {
        log.info("Deleting client with ID: {}", clientId);
        if (!clientRepo.existsById(clientId)) {
            throw new IllegalArgumentException("Client not found with ID: " + clientId);
        }
        clientRepo.deleteById(clientId);
    }
}