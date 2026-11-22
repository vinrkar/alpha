package com.vrevankar.alpha.fortune.client.entity;

import jakarta.persistence.*;
import lombok.*;
import java.util.UUID;

@Entity
@Table(name = "CLIENT_IDENTITY")
@IdClass(ClientIdentityId.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ClientIdentity {

    @Id
    @Column(name = "CLIENT_ID", nullable = false, columnDefinition = "RAW(16)")
    private UUID clientId;

    @Id
    @Column(name = "ID_TYP", nullable = false, length = 30)
    private String idTyp;

    @Column(name = "ID_VAL", nullable = false, length = 20)
    private String idVal;

    @MapsId("clientId") // Automatically populates clientId from the Client relationship
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "CLIENT_ID", nullable = false)
    private Client client;
}