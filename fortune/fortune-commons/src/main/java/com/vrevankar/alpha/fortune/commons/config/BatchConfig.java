package com.vrevankar.alpha.fortune.commons.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "spring.batch")
@Getter
@Setter
public class BatchConfig {

    private AddressBatchConfig address = new AddressBatchConfig();
    private ClientConfig client = new ClientConfig();

    @Getter
    @Setter
    public static class AddressBatchConfig {
        private RoutineConfig routine = new RoutineConfig();
        private RoutineConfig routineRetry = new RoutineConfig();

        @Getter
        @Setter
        public static class RoutineConfig {
            private String cron;
        }
    }

    @Getter
    @Setter
    public static class ClientConfig {
        private NominatimConfig nominatim = new NominatimConfig();

        @Getter
        @Setter
        public static class NominatimConfig {
            private String baseUrl;
            private String searchPath;
            private String userAgent;
        }
    }
}