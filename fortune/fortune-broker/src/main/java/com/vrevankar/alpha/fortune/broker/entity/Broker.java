package com.vrevankar.alpha.fortune.broker.entity;

import com.vrevankar.alpha.fortune.commons.entity.Address;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "BROKER")
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Broker {

    @Id
    @Column(name = "DP_ID")
    private String dpId;

    @Column(name = "NAME", nullable = false)
    private String name;

    @Column(name = "BROKER_CD", nullable = false)
    private String brokerCd;

    @Column(name = "PAN", nullable = false)
    private String pan;

    @Column(name = "SEBI_REGN_NO", nullable = false)
    private String sebiRegnNo;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "ADDR_ID", nullable = false)
    private Address address;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "SEC_ADDR_ID", nullable = false)
    private Address secondaryAddress;

    @Column(name = "WEB", nullable = false)
    private String web;

    @Column(name = "ACTIVE", nullable = false)
    @Builder.Default
    private String active = "Y";

    @Column(name = "STATUS", nullable = false)
    @Builder.Default
    private String status = "PENDING_ENRICHMENT";

    @CreationTimestamp
    @Column(name = "CRT_DTTM", nullable = false, updatable = false)
    private LocalDateTime crtDttm;

    @UpdateTimestamp
    @Column(name = "UPDT_DTTM", nullable = false)
    private LocalDateTime updtDttm;
}