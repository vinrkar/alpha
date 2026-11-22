package com.vrevankar.alpha.fortune.commons.service;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

@Service
@ConditionalOnProperty(name = "spring.mail.host")
@Slf4j
@AllArgsConstructor
public class EmailService {

    private final JavaMailSender mailSender;

    public void sendEmailAsync(String to, String subject, String body) {
        log.info("[VirtualThread-{}] Dispatching email to: {}", Thread.currentThread().threadId(), to);

        Thread.ofVirtual().start(() -> {
            try {
                SimpleMailMessage message = new SimpleMailMessage();
                message.setTo(to);
                message.setSubject(subject);
                message.setText(body);
                mailSender.send(message);
                log.info("[VirtualThread-{}] Email successfully sent to: {}", Thread.currentThread().threadId(), to);
            } catch (Exception e) {
                log.error("[VirtualThread-{}] Failed to send email to {}: {}",
                        Thread.currentThread().threadId(), to, e.getMessage(), e);
            }
        });
    }
}