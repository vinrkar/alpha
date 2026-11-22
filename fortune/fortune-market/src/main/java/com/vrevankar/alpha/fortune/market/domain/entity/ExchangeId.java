package com.vrevankar.alpha.fortune.market.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.*;

import java.io.Serializable;
import java.time.LocalDate;

@Embeddable
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode
public class ExchangeId implements Serializable {

    @Column(name = "XCHG_ID", nullable = false)
    private Long xchgId;

    @Column(name = "XCHG_DT", nullable = false)
    private LocalDate xchgDt;
}