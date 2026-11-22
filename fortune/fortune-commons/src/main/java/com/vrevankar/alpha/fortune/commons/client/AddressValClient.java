package com.vrevankar.alpha.fortune.commons.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.web.client.RestClient;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
public class AddressValClient {

    private final RestClient restClient;
    private final String searchPath;

    public AddressValClient(RestClient restClient, String searchPath) {
        this.restClient = restClient;
        this.searchPath = searchPath;
    }

    public boolean validateAddress(String street, String city, String pin, String isoCd) {
        return fetchNominatimDetails(street, city, pin, isoCd) != null;
    }

    public Map<String, Object> fetchNominatimDetails(String street, String city, String pin, String isoCd) {
        try {
            Thread.sleep(1000); // Rate limit protection (1 req/sec)

            String query = String.format("%s, %s, %s, %s", street, city, pin, isoCd);

            List<Map<String, Object>> response = restClient.get()
                    .uri(uriBuilder -> uriBuilder
                            .path(searchPath)
                            .queryParam("q", query)
                            .queryParam("format", "json")
                            .queryParam("addressdetails", "1")
                            .queryParam("limit", 1)
                            .build())
                    .retrieve()
                    .body(new ParameterizedTypeReference<>() {});

            if (response != null && !response.isEmpty()) {
                return response.get(0);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (Exception e) {
            log.error("Failed to fetch live details from Nominatim: {}", e.getMessage());
        }
        return null;
    }

    public Map<String, String> fetchAddressDetails(String street, String city, String pin, String isoCd) {
        Map<String, Object> topResult = fetchNominatimDetails(street, city, pin, isoCd);

        if (topResult != null && topResult.get("address") instanceof Map<?, ?> rawMap) {
            Map<String, String> stringMap = new HashMap<>();
            for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
                if (entry.getKey() instanceof String key && entry.getValue() instanceof String val) {
                    stringMap.put(key, val);
                }
            }
            return stringMap;
        }
        return Collections.emptyMap();
    }
}