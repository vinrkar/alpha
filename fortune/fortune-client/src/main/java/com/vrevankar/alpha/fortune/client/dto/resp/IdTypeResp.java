package com.vrevankar.alpha.fortune.client.dto.resp;

import com.vrevankar.alpha.fortune.client.entity.IdType;

public record IdTypeResp(
        String idTyp,
        String regex,
        Boolean active // true if 'Y', false if 'N'
) {
    public static IdTypeResp fromEntity(IdType entity) {
        return new IdTypeResp(
                entity.getIdTyp(),
                entity.getRegex(),
                "Y".equalsIgnoreCase(entity.getActive())
        );
    }
}