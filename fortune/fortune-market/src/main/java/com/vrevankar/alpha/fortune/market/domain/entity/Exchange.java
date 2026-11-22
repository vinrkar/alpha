package com.vrevankar.alpha.fortune.market.domain.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "EXCHANGE")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Exchange {

    @EmbeddedId
    private ExchangeId id;

    @MapsId("xchgId") // Maps the xchgId part of the embedded ID to this relationship
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "XCHG_ID", nullable = false)
    private ExchangeMaster exchangeMaster;

    @Column(name = "XCHG_RT", nullable = false, precision = 18, scale = 6)
    private BigDecimal xchgRt;

    @Column(name = "UPDT_DTTM", nullable = false)
    private LocalDateTime updtDttm;
}