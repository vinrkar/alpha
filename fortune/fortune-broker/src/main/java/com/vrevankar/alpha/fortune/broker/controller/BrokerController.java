package com.vrevankar.alpha.fortune.broker.controller;

import com.vrevankar.alpha.fortune.broker.dto.BrokerReqDto;
import com.vrevankar.alpha.fortune.broker.dto.BrokerRespDto;
import com.vrevankar.alpha.fortune.broker.service.BrokerService;
import com.vrevankar.alpha.fortune.commons.dto.BrokerStatusResp;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/broker")
@RequiredArgsConstructor
public class BrokerController {

    private final BrokerService brokerService;

    @PostMapping
    public ResponseEntity<BrokerRespDto> createBroker(@Valid @RequestBody BrokerReqDto reqDto) {
        return ResponseEntity.status(HttpStatus.CREATED).body(brokerService.createBroker(reqDto));
    }

    @GetMapping
    public ResponseEntity<List<BrokerRespDto>> getAllBrokers() {
        return ResponseEntity.ok(brokerService.getAllBrokers());
    }

    @GetMapping("/{dpId}")
    public ResponseEntity<BrokerRespDto> getBrokerById(@PathVariable Long dpId) {
        return ResponseEntity.ok(brokerService.getBrokerById(dpId));
    }

    @GetMapping("/{dpId}/status")
    public ResponseEntity<BrokerStatusResp> getBrokerStatus(@PathVariable Long dpId) {
        return ResponseEntity.ok(brokerService.getBrokerStatus(dpId));
    }

    @DeleteMapping("/{dpId}")
    public ResponseEntity<Void> deleteBroker(@PathVariable Long dpId) {
        brokerService.deleteBroker(dpId);
        return ResponseEntity.noContent().build();
    }
}