package com.vrevankar.alpha.fortune.market.domain.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.UuidGenerator;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

import static com.vrevankar.alpha.fortune.market.common.enums.SecurityStatus.PENDING_ENRICHMENT;

@Entity
@Table(name = "SECURITY_MASTER")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SecurityMaster {

    @Id
    @GeneratedValue
    @UuidGenerator
    @Column(name = "SEC_ID", columnDefinition = "RAW(16)", updatable = false, nullable = false)
    private UUID secId;

    @Column(name = "ISIN", length = 12, nullable = false, unique = true)
    private String isin;

    @Column(name = "TICKER", length = 10, nullable = false)
    private String ticker;

    @Column(name = "SEC_NM", length = 100, nullable = false)
    private String secNm;

    @Column(name = "XCHG", length = 8, nullable = false)
    private String xchg;

    @Column(name = "CURR", length = 3, nullable = false)
    @Builder.Default
    private String curr = "INR";

    @Convert(converter = org.hibernate.type.YesNoConverter.class)
    @Column(name = "ACTIVE", length = 1, nullable = false)
    @Builder.Default
    private Boolean active = true;

    @Column(name = "START_DT", nullable = false)
    private LocalDate startDt;

    @Column(name = "END_DT")
    private LocalDate endDt;

    @Column(name = "STATUS", length = 20, nullable = false)
    @Builder.Default
    private String status = PENDING_ENRICHMENT.name();

    @Column(name = "RTY_CNT", nullable = false)
    @Builder.Default
    private Integer retryCount = 0;

    @Column(name = "NXT_RTY_DTTM")
    private LocalDateTime nextRetryAt;

    @Column(name = "CRT_DTTM", nullable = false, updatable = false)
    private LocalDateTime crtDttm;

    @Column(name = "UPDT_DTTM", nullable = false)
    private LocalDateTime updtDttm;

    @PrePersist
    protected void onCreate() {
        LocalDateTime now = LocalDateTime.now();
        if (crtDttm == null) crtDttm = now;
        if (updtDttm == null) updtDttm = now;
    }

    @PreUpdate
    protected void onUpdate() {
        updtDttm = LocalDateTime.now();
    }
}