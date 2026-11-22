package com.vrevankar.alpha.fortune.market;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class FortuneMarketApp {
	public static void main(String... args) {
		SpringApplication.run(FortuneMarketApp.class, args);
	}
}