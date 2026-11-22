package com.vrevankar.alpha.fortune.commons.service;

import org.jasypt.encryption.pbe.StandardPBEStringEncryptor;
import org.jasypt.encryption.pbe.config.EnvironmentPBEConfig;
import org.jasypt.iv.RandomIvGenerator;
import org.jasypt.salt.RandomSaltGenerator;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class Encryptor {

    @Value("${jasypt.encryptor.algorithm:PBEWithHMACSHA512ANDAES_256}")
    private String encAlg;

    @Value("${jasypt.encryptor.password:FORTUNE_DEFAULT_SECRET_KEY}")
    private String encSecretKey;

    public StandardPBEStringEncryptor getEncryptor() {
        StandardPBEStringEncryptor encryptor = new StandardPBEStringEncryptor();

        EnvironmentPBEConfig config = new EnvironmentPBEConfig();
        config.setAlgorithm(encAlg);
        config.setPassword(encSecretKey);
        config.setIvGenerator(new RandomIvGenerator());
        config.setSaltGenerator(new RandomSaltGenerator());

        encryptor.setConfig(config);

        return encryptor;
    }
}