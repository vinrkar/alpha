package com.vrevankar.alpha.fortune.client.controller;

import com.vrevankar.alpha.fortune.client.dto.req.IdTypeReq;
import com.vrevankar.alpha.fortune.client.dto.resp.IdTypeResp;
import com.vrevankar.alpha.fortune.client.service.IdTypeService;
import com.vrevankar.alpha.fortune.client.validation.IdTypeGroups;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/client/id-type")
@RequiredArgsConstructor
public class IdTypeController {

    private final IdTypeService idTypeService;

    @GetMapping
    public ResponseEntity<List<IdTypeResp>> getIdTypes(
            @RequestParam(required = false) String active) {
        List<IdTypeResp> idTypes = idTypeService.getIdTypes(active);
        return ResponseEntity.ok(idTypes);
    }

    @GetMapping("/{idTyp}")
    public ResponseEntity<IdTypeResp> getIdTypeById(@PathVariable String idTyp) {
        return ResponseEntity.ok(idTypeService.getIdTypeById(idTyp));
    }

    @PostMapping
    public ResponseEntity<IdTypeResp> createIdType(
            @Validated(IdTypeGroups.Create.class) @RequestBody IdTypeReq requestDto) {
        IdTypeResp created = idTypeService.createIdType(requestDto);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @PatchMapping("/{idTyp}")
    public ResponseEntity<IdTypeResp> patchIdType(
            @PathVariable String idTyp,
            @Validated(IdTypeGroups.Update.class) @RequestBody IdTypeReq requestDto) {
        IdTypeResp updated = idTypeService.patchIdType(idTyp, requestDto);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{idTyp}")
    public ResponseEntity<Void> deleteIdType(@PathVariable String idTyp) {
        idTypeService.deleteIdType(idTyp);
        return ResponseEntity.noContent().build();
    }
}