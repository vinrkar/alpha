package com.vrevankar.alpha.fortune.market.domain.entity;

import lombok.*;

import java.io.Serializable;
import java.time.LocalDate;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode
public class SecurityId implements Serializable {
    private String isin;
    private LocalDate tradeDt;
}