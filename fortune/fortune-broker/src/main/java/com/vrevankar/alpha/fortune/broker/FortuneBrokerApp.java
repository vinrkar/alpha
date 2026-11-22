package com.vrevankar.alpha.fortune.broker;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@ComponentScan(basePackages = {
        "com.vrevankar.alpha.fortune.broker",
        "com.vrevankar.alpha.fortune.commons"
})
@EntityScan(basePackages = {
        "com.vrevankar.alpha.fortune.broker.entity",
        "com.vrevankar.alpha.fortune.commons"
})
@EnableJpaRepositories(basePackages = {
        "com.vrevankar.alpha.fortune.broker",
        "com.vrevankar.alpha.fortune.commons"
})
public class FortuneBrokerApp {
    public static void main(String[] args) {
        SpringApplication.run(FortuneBrokerApp.class, args);
    }
}