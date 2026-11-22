package com.vrevankar.alpha.fortune.client.service;

import com.vrevankar.alpha.fortune.client.dto.req.ClientPatchReq;
import com.vrevankar.alpha.fortune.client.dto.req.ClientReq;
import com.vrevankar.alpha.fortune.client.dto.resp.ClientResp;

import java.util.List;
import java.util.UUID;

public interface ClientService {
    ClientResp onboardClient(ClientReq req);
    List<ClientResp> getAllClients();
    ClientResp getClientById(UUID clientId);
    ClientResp patchClient(UUID clientId, ClientPatchReq req);
    void deleteClient(UUID clientId);
}