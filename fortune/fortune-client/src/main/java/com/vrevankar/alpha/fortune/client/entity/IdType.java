package com.vrevankar.alpha.fortune.client.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "ID_TYPE")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IdType {

    @Id
    @Column(name = "ID_TYP", length = 30, nullable = false)
    private String idTyp;

    @Column(name = "REGEX", length = 60)
    private String regex;

    @Column(name = "ACTIVE", length = 1, nullable = false)
    @Builder.Default
    private String active = "Y";
}