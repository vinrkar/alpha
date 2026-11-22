package com.vrevankar.alpha.fortune.client.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.annotations.UuidGenerator;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "WALLET", uniqueConstraints = {
        @UniqueConstraint(name = "UK__WALLET__CLIENT_ID__BANK_NM__ACC_TYP__ACC_NO", columnNames = {"CLIENT_ID", "BANK_NM", "ACC_TYP", "ACC_NO"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Wallet {

    @Id
    @GeneratedValue
    @UuidGenerator
    @Column(name = "WALLET_ID", nullable = false, updatable = false, columnDefinition = "RAW(16)")
    private UUID walletId;

    @Column(name = "CURR", nullable = false, length = 3)
    @Builder.Default
    private String curr = "INR";

    @Column(name = "BANK_NM", nullable = false, length = 30)
    private String bankNm;

    @Column(name = "ACC_TYP", nullable = false, length = 10)
    private String accTyp; // "SAVINGS" or "PIS"

    @Column(name = "ACC_NO", nullable = false, length = 14)
    private String accNo;

    @Column(name = "BAL_AMT", nullable = false, precision = 15, scale = 4)
    @Builder.Default
    private BigDecimal balAmt = BigDecimal.ZERO;

    @Column(name = "BLOCKED_AMT", nullable = false, precision = 15, scale = 4)
    @Builder.Default
    private BigDecimal blockedAmt = BigDecimal.ZERO;

    @CreationTimestamp
    @Column(name = "CRT_DTTM", nullable = false, updatable = false)
    private LocalDateTime crtDttm;

    @UpdateTimestamp
    @Column(name = "UPDT_DTTM", nullable = false)
    private LocalDateTime updtDttm;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "CLIENT_ID", nullable = false)
    private Client client;
}