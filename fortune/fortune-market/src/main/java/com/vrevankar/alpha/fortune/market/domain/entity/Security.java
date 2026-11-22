package com.vrevankar.alpha.fortune.market.domain.entity;

import com.vrevankar.alpha.fortune.market.domain.dto.SecurityDto;
import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "SECURITY", indexes = {
        @Index(name = "IDX__SECURITY__TRD_DT", columnList = "TRD_DT")
})
@IdClass(SecurityId.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@EntityListeners(AuditingEntityListener.class)
public class Security {

    @Id
    @Column(name = "ISIN", length = 12, nullable = false)
    private String isin;

    @Id
    @Column(name = "TRADE_DT", nullable = false)
    private LocalDate tradeDt;

    @Column(name = "PRICE", precision = 12, scale = 2, nullable = false)
    private BigDecimal price;

    @LastModifiedDate
    @Column(name = "UPDT_DTTM", nullable = false)
    private LocalDateTime updtDttm;

    @PrePersist
    @PreUpdate
    public void prePersistOrUpdate() {
        this.updtDttm = LocalDateTime.now();
    }

    public static Security from(SecurityDto dto) {
        return Security.builder()
                .isin(dto.isin())
                .tradeDt(dto.tradeDt())
                .price(dto.price())
                .build();
    }

}