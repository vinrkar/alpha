package com.vrevankar.alpha.fortune.commons.entity;

import com.vrevankar.alpha.fortune.commons.enums.AddressStatus;
import jakarta.persistence.*;
import lombok.*;

import java.util.UUID;

@Entity
@Table(name = "ADDRESS")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Address {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    @Column(name = "ADDR_ID", nullable = false, columnDefinition = "RAW(16)")
    private UUID addrId;

    @Column(name = "STREET", nullable = false, length = 100)
    private String street;

    @Column(name = "CITY", nullable = false, length = 30)
    private String city;

    @Column(name = "PIN", nullable = false, length = 6)
    private String pin;

    @Column(name = "ISO_CD", nullable = false, length = 6)
    private String isoCd;

    @Column(name = "PH_NO", nullable = false, length = 20)
    private String phNo;

    @Column(name = "EMAIL", nullable = false, length = 60)
    private String email;

    @Enumerated(EnumType.STRING)
    @Column(name = "STATUS", nullable = false, length = 30, insertable = false)
    @Builder.Default
    private AddressStatus status = AddressStatus.PENDING_ENRICHMENT;

}