package com.vrevankar.alpha.fortune.client.entity;

import com.vrevankar.alpha.fortune.commons.converter.YesNoBooleanConverter;
import com.vrevankar.alpha.fortune.commons.entity.Address;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.annotations.UuidGenerator;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "CLIENT", uniqueConstraints = {
        @UniqueConstraint(name = "UK__CLIENT__DP_ID__CLIENT_CD", columnNames = {"DP_ID", "CLIENT_CD"}),
        @UniqueConstraint(name = "UK__CLIENT__DP_ID__TRADE__CD", columnNames = {"DP_ID", "TRADE_CD"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Client {

    @Id
    @GeneratedValue
    @UuidGenerator
    @Column(name="CLIENT_ID", nullable=false, updatable=false, columnDefinition="RAW(16)")
    private UUID clientId;

    @Column(name="DP_ID", nullable=false)
    private String dpId;

    @Column(name="CLIENT_CD", nullable=false, length=8)
    private String clientCd;

    @Column(name="TRADE_CD", nullable=false, length=8)
    private String tradeCd;

    @Column(name="FIRST_NM", nullable=false, length=30)
    private String firstNm;

    @Column(name="LAST_NM", nullable=false, length=30)
    private String lastNm;

    @Column(name="PH_NO", nullable=false, length=20)
    private String phNo;

    @Column(name="EMAIL", nullable=false, length=60)
    private String email;

    @Column(name="PASSWORD", nullable=false, length=100)
    private String password;

    @Column(name="ACC_TYP", nullable=false, length=3)
    @Builder.Default
    private String accTyp="NRO";

    @Convert(converter=YesNoBooleanConverter.class)
    @Column(name="PIS", nullable=false, length=1)
    @Builder.Default
    private Boolean pis=false;

    @OneToOne(cascade=CascadeType.ALL, fetch=FetchType.LAZY, optional=false)
    @JoinColumn(name="ADDR_ID", nullable=false)
    private Address address;

    @Column(name="ACC_OPEN_DT", nullable=false)
    private LocalDate accOpenDt;

    @Column(name="ACC_CLOSE_DT")
    private LocalDate accCloseDt;

    @CreationTimestamp
    @Column(name="CRT_DTTM", nullable=false, updatable=false)
    private LocalDateTime crtDttm;

    @UpdateTimestamp
    @Column(name="UPDT_DTTM", nullable=false)
    private LocalDateTime updtDttm;

    @OneToMany(mappedBy="client", cascade=CascadeType.ALL, orphanRemoval=true)
    @Builder.Default
    private List<ClientIdentity> identities=new ArrayList<>();

    @OneToMany(mappedBy="client", cascade=CascadeType.ALL, orphanRemoval=true)
    @Builder.Default
    private List<Wallet> wallets=new ArrayList<>();

    public void addIdentity(ClientIdentity identity) {
        identities.add(identity);
        identity.setClient(this);
    }

    public void addWallet(Wallet wallet) {
        wallets.add(wallet);
        wallet.setClient(this);
    }
}