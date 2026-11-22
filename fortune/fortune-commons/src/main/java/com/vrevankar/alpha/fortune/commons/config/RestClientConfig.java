package com.vrevankar.alpha.fortune.commons.config;

import com.vrevankar.alpha.fortune.commons.client.AddressValClient;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestClient;

@AutoConfiguration
public class RestClientConfig {

    @Bean
    public RestClient fortuneMarket(
            @Value("${fortune.market.base-url:http://fortune-market-local.alpha.com}") String marketBaseUrl,
            RestClient.Builder builder) {
        return builder.baseUrl(marketBaseUrl).build();
    }

    @Bean
    public RestClient fortuneBroker(
            @Value("${fortune.broker.base-url:http://fortune-broker-local.alpha.com}") String brokerBaseUrl,
            RestClient.Builder builder) {
        return builder.baseUrl(brokerBaseUrl).build();
    }

    @Bean
    public RestClient fortuneClient(
            @Value("${fortune.client.base-url:http://fortune-client-local.alpha.com}") String clientBaseUrl,
            RestClient.Builder builder) {
        return builder.baseUrl(clientBaseUrl).build();
    }

    @Bean
    RestClient nominatimRestClient(
            @Value("${external.nominatim.base-url:https://nominatim.openstreetmap.org}") String baseUrl,
            @Value("${external.user-agent:Fortune/1.0}") String userAgent,
            RestClient.Builder builder) {
        return builder.baseUrl(baseUrl)
                .defaultHeader("User-Agent", userAgent)
                .build();
    }

    @Bean
    public AddressValClient addressValClient(
            @Qualifier("nominatimRestClient") RestClient nominatimRRestClient,
            @Value("${external.search-path:/search}") String searchPath) {
        return new AddressValClient(nominatimRRestClient, searchPath);
    }

    @Bean
    public RestClient yahooFinanceRestClient(
            @Value("${external.yahoo-finance.base-url:https://query2.finance.yahoo.com}") String baseUrl,
            @Value("${external.user-agent:Fortune/1.0}") String userAgent,
            RestClient.Builder builder) {
        return builder.baseUrl(baseUrl)
                .defaultHeader("User-Agent", userAgent)
                .build();
    }

    @Bean
    public RestClient frankfurterRestClient(
            @Value("${external.frankfurter.base-url:https://api.frankfurter.dev}") String baseUrl,
            @Value("${external.user-agent:Fortune/1.0}") String userAgent,
            RestClient.Builder builder) {
        return builder.baseUrl(baseUrl)
                .defaultHeader("User-Agent", userAgent)
                .build();
    }
}