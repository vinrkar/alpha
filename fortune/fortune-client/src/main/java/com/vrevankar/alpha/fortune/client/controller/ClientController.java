package com.vrevankar.alpha.fortune.client.controller;

import com.vrevankar.alpha.fortune.client.dto.req.ClientPatchReq;
import com.vrevankar.alpha.fortune.client.dto.req.ClientReq;
import com.vrevankar.alpha.fortune.client.dto.resp.ClientResp;
import com.vrevankar.alpha.fortune.client.service.ClientService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/client")
@RequiredArgsConstructor
public class ClientController {

    private final ClientService clientService;

    @PostMapping
    public ResponseEntity<ClientResp> onboardClient(@RequestBody @Valid ClientReq request) {
        ClientResp response = clientService.onboardClient(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping
    public ResponseEntity<List<ClientResp>> getAllClients() {
        List<ClientResp> clients = clientService.getAllClients();
        return ResponseEntity.ok(clients);
    }

    @GetMapping("/{clientId}")
    public ResponseEntity<ClientResp> getClientById(@PathVariable UUID clientId) {
        ClientResp response = clientService.getClientById(clientId);
        return ResponseEntity.ok(response);
    }

    @PatchMapping("/{clientId}")
    public ResponseEntity<ClientResp> patchClient(
            @PathVariable UUID clientId,
            @RequestBody @Valid ClientPatchReq request) {
        ClientResp response = clientService.patchClient(clientId, request);
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/{clientId}")
    public ResponseEntity<Void> deleteClient(@PathVariable UUID clientId) {
        clientService.deleteClient(clientId);
        return ResponseEntity.noContent().build();
    }
}