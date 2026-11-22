package com.vrevankar.alpha.fortune.market.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "SECURITY_INGESTION_STATE")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SecurityIngestionState {

    @Id
    @Column(name = "JOB_NM", length = 30, nullable = false)
    private String jobNm;

    @Column(name = "TRADE_DT", nullable = false)
    private LocalDate tradeDt;

    @UpdateTimestamp
    @Column(name = "UPDT_DTTM", nullable = false)
    private LocalDateTime updtDttm;
}