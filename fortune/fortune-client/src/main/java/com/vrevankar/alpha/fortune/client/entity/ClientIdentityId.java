package com.vrevankar.alpha.fortune.client.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.UUID;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ClientIdentityId implements Serializable {
    private UUID clientId;
    private String idTyp;
}