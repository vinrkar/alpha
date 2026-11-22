package com.vrevankar.alpha.fortune.client;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@ComponentScan(basePackages = {
        "com.vrevankar.alpha.fortune.client",
        "com.vrevankar.alpha.fortune.commons"
})
@EntityScan(basePackages = {
        "com.vrevankar.alpha.fortune.client.entity",
        "com.vrevankar.alpha.fortune.commons.entity"
})
public class FortuneClientApp {
    public static void main(String... args) {
        SpringApplication.run(FortuneClientApp.class, args);
    }
}