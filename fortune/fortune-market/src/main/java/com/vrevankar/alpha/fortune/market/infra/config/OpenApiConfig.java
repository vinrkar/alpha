package com.vrevankar.alpha.fortune.market.infra.config;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.info.Info;
import org.springframework.context.annotation.Configuration;

@Configuration
@OpenAPIDefinition(
        info = @Info(
                title = "Fortune Market API",
                version = "1.0.0",
                description = "API documentation for tracking portfolio performance, XIRR, and CAGR calculations."
        )
)
public class OpenApiConfig {
}