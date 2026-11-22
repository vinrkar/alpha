package com.vrevankar.alpha.fortune.market.domain.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "EXCHANGE_MASTER", uniqueConstraints = {
        @UniqueConstraint(name = "UK__EXCHANGE_MASTER__CURR", columnNames = {"FR_CURR", "TO_CURR"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ExchangeMaster {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "xchg_seq_gen")
    @SequenceGenerator(name = "xchg_seq_gen", sequenceName = "SEQ__EXCHANGE_MASTER__XCHG_ID", allocationSize = 1)
    @Column(name = "XCHG_ID", nullable = false, updatable = false)
    private Long xchgId;

    @NotNull
    @Pattern(regexp = "^[A-Z]{3}$")
    @Column(name = "FR_CURR", length = 3, nullable = false)
    private String frCurr;

    @NotNull
    @Pattern(regexp = "^[A-Z]{3}$")
    @Column(name = "TO_CURR", length = 3, nullable = false)
    private String toCurr;

    @NotNull
    @Column(name = "ACTIVE", length = 1, nullable = false)
    @Builder.Default
    private String active = "Y";

    @CreationTimestamp
    @Column(name = "CRT_DTTM", nullable = false, updatable = false)
    private LocalDateTime crtDttm;

    @UpdateTimestamp
    @Column(name = "UPDT_DTTM", nullable = false)
    private LocalDateTime updtDttm;

    @PrePersist
    protected void onCreate() {
        LocalDateTime now = LocalDateTime.now();
        this.crtDttm = now;
        this.updtDttm = now;
    }

    @PreUpdate
    protected void onUpdate() {
        this.updtDttm = LocalDateTime.now();
    }

}