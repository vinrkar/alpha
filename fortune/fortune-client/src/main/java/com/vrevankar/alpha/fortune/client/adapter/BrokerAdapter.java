package com.vrevankar.alpha.fortune.client.adapter;

import com.vrevankar.alpha.fortune.commons.dto.BrokerStatusResp;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

@Component
public class BrokerAdapter {

    private final RestClient brokerClient;

    public BrokerAdapter(@Qualifier("fortuneBroker") RestClient brokerClient) {
        this.brokerClient = brokerClient;
    }

    public void validateBrokerActive(String dpId) {
        try {
            BrokerStatusResp resp = brokerClient.get()
                    .uri("/api/v1/broker/{dpId}/status", dpId)
                    .retrieve()
                    .body(BrokerStatusResp.class);

            if (resp == null || !resp.active()) {
                throw new IllegalArgumentException("Broker with DP ID " + dpId + " is not active.");
            }
        } catch (RestClientResponseException e) {
            if (e.getStatusCode().value() == 404) {
                throw new IllegalArgumentException("Broker with DP ID " + dpId + " does not exist.");
            }
            throw e;
        }
    }
}