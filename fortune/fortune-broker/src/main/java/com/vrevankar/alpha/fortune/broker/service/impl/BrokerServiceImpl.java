package com.vrevankar.alpha.fortune.broker.service.impl;

import com.vrevankar.alpha.fortune.broker.dto.BrokerReqDto;
import com.vrevankar.alpha.fortune.broker.dto.BrokerRespDto;
import com.vrevankar.alpha.fortune.broker.entity.Broker;
import com.vrevankar.alpha.fortune.broker.repository.BrokerRepo;
import com.vrevankar.alpha.fortune.broker.service.BrokerService;
import com.vrevankar.alpha.fortune.commons.client.AddressValClient;
import com.vrevankar.alpha.fortune.commons.dto.AddressResp;
import com.vrevankar.alpha.fortune.commons.dto.BrokerStatusResp;
import com.vrevankar.alpha.fortune.commons.entity.Address;
import com.vrevankar.alpha.fortune.commons.enums.AddressStatus;
import com.vrevankar.alpha.fortune.commons.repository.AddressRepo;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class BrokerServiceImpl implements BrokerService {

    private final BrokerRepo brokerRepo;
    private final AddressRepo addressRepo;
    private final AddressValClient addressValClient;

    @Override
    @Transactional
    public BrokerRespDto createBroker(BrokerReqDto reqDto) {
        // 1. Build and persist Primary Address
        Address primaryAddress = Address.builder()
                .street(reqDto.primaryAddress().street())
                .city(reqDto.primaryAddress().city())
                .pin(reqDto.primaryAddress().pin())
                .isoCd(reqDto.primaryAddress().isoCd().toUpperCase())
                .phNo(reqDto.primaryAddress().phNo())
                .email(reqDto.primaryAddress().email().toLowerCase())
                .status(AddressStatus.PENDING_ENRICHMENT)
                .build();
        Address savedPrimary = addressRepo.save(primaryAddress);

        // 2. Build and persist Secondary Address
        Address secondaryAddress = Address.builder()
                .street(reqDto.secondaryAddress().street())
                .city(reqDto.secondaryAddress().city())
                .pin(reqDto.secondaryAddress().pin())
                .isoCd(reqDto.secondaryAddress().isoCd().toUpperCase())
                .phNo(reqDto.secondaryAddress().phNo())
                .email(reqDto.secondaryAddress().email().toLowerCase())
                .status(AddressStatus.PENDING_ENRICHMENT)
                .build();
        Address savedSecondary = addressRepo.save(secondaryAddress);

        // 3. Build and persist Broker linking addresses and new attributes
        Broker broker = Broker.builder()
                .dpId(reqDto.dpId())
                .name(reqDto.name())
                .brokerCd(reqDto.brokerCd().toUpperCase())
                .pan(reqDto.pan().toUpperCase())
                .sebiRegnNo(reqDto.sebiRegnNo())
                .address(savedPrimary)
                .secondaryAddress(savedSecondary)
                .web(reqDto.web())
                .active(reqDto.active() != null ? reqDto.active().toUpperCase() : "Y")
                .status(reqDto.status() != null ? reqDto.status().toUpperCase() : "PENDING_ENRICHMENT")
                .build();

        Broker savedBroker = brokerRepo.save(broker);
        log.info("Successfully created Broker with DP ID: {}", savedBroker.getDpId());

        return mapToDto(savedBroker);
    }

    @Override
    @Transactional(readOnly = true)
    public List<BrokerRespDto> getAllBrokers() {
        return brokerRepo.findAll().stream()
                .map(this::mapToDto)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public BrokerRespDto getBrokerById(Long dpId) {
        Broker broker = brokerRepo.findById(dpId)
                .orElseThrow(() -> new IllegalArgumentException("Broker not found for DP ID: " + dpId));
        return mapToDto(broker);
    }

    @Override
    @Transactional
    public void deleteBroker(Long dpId) {
        if (!brokerRepo.existsById(dpId)) {
            throw new IllegalArgumentException("Broker not found for DP ID: " + dpId);
        }
        brokerRepo.deleteById(dpId);
    }

    @Override
    @Transactional(readOnly = true)
    public BrokerStatusResp getBrokerStatus(Long dpId) {
        log.debug("Fetching broker status for DP ID: {}", dpId);

        Broker broker = brokerRepo.findById(dpId)
                .orElseThrow(() -> new IllegalArgumentException("Broker not found with DP ID: " + dpId));

        boolean isActive = "Y".equalsIgnoreCase(broker.getActive()) && "COMPLETED".equalsIgnoreCase(broker.getStatus());

        return new BrokerStatusResp(
                broker.getDpId(),
                broker.getStatus(),
                isActive
        );
    }

    private BrokerRespDto mapToDto(Broker broker) {
        Map<String, String> primaryDetails = addressValClient.fetchAddressDetails(
                broker.getAddress().getStreet(),
                broker.getAddress().getCity(),
                broker.getAddress().getPin(),
                broker.getAddress().getIsoCd()
        );
        AddressResp primaryDto = AddressResp.fromEntity(
                broker.getAddress(),
                primaryDetails.get("state"),
                primaryDetails.get("country")
        );

        Map<String, String> secondaryDetails = addressValClient.fetchAddressDetails(
                broker.getSecondaryAddress().getStreet(),
                broker.getSecondaryAddress().getCity(),
                broker.getSecondaryAddress().getPin(),
                broker.getSecondaryAddress().getIsoCd()
        );
        AddressResp secondaryDto = AddressResp.fromEntity(
                broker.getSecondaryAddress(),
                secondaryDetails.get("state"),
                secondaryDetails.get("country")
        );

        return BrokerRespDto.fromEntity(broker, primaryDto, secondaryDto);
    }
}