package com.vrevankar.alpha.fortune.client.service;

import com.vrevankar.alpha.fortune.client.dto.req.IdTypeReq;
import com.vrevankar.alpha.fortune.client.dto.resp.IdTypeResp;

import java.util.List;

public interface IdTypeService {

    List<IdTypeResp> getIdTypes(String active);

    IdTypeResp getIdTypeById(String idTyp);

    IdTypeResp createIdType(IdTypeReq requestDto);

    IdTypeResp patchIdType(String idTyp, IdTypeReq requestDto);

    void deleteIdType(String idTyp);
}
