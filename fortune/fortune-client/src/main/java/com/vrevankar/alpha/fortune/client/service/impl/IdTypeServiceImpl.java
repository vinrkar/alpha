package com.vrevankar.alpha.fortune.client.service.impl;

import com.vrevankar.alpha.fortune.client.dto.req.IdTypeReq;
import com.vrevankar.alpha.fortune.client.dto.resp.IdTypeResp;
import com.vrevankar.alpha.fortune.client.entity.IdType;
import com.vrevankar.alpha.fortune.client.repository.IdTypeRepo;
import com.vrevankar.alpha.fortune.client.service.IdTypeService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class IdTypeServiceImpl implements IdTypeService {

    private final IdTypeRepo idTypeRepo;

    @Override
    @Transactional(readOnly = true)
    public List<IdTypeResp> getIdTypes(String active) {
        if (active != null) {
            String dbActive;

            // Map intuitive inputs (true/false, y/n) to DB representation ('Y'/'N')
            if (active.equalsIgnoreCase("true") || active.equalsIgnoreCase("y")) {
                dbActive = "Y";
            } else if (active.equalsIgnoreCase("false") || active.equalsIgnoreCase("n")) {
                dbActive = "N";
            } else {
                throw new IllegalArgumentException("Invalid 'active' query parameter. Expected true, false, Y, or N.");
            }

            log.debug("Fetching identity types filtered by active status: {}", dbActive);
            return idTypeRepo.findByActive(dbActive).stream()
                    .map(IdTypeResp::fromEntity)
                    .toList();
        }

        log.debug("Fetching all identity types");
        return idTypeRepo.findAll().stream()
                .map(IdTypeResp::fromEntity)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public IdTypeResp getIdTypeById(String idTyp) {
        String normalizedKey = idTyp != null ? idTyp.toUpperCase() : "";
        log.debug("Fetching identity type by code: {}", normalizedKey);

        IdType entity = idTypeRepo.findById(normalizedKey)
                .orElseThrow(() -> new IllegalArgumentException("Identity type not found: " + normalizedKey));

        return IdTypeResp.fromEntity(entity);
    }

    @Override
    @Transactional
    public IdTypeResp createIdType(IdTypeReq requestDto) {
        String normalizedKey = requestDto.idTyp() != null ? requestDto.idTyp().toUpperCase() : "";
        log.debug("Creating new identity type: {}", normalizedKey);

        if (idTypeRepo.existsById(normalizedKey)) {
            throw new IllegalArgumentException("Identity type already exists: " + normalizedKey);
        }

        // Normalizes Y/y/true/TRUE -> 'Y' and N/n/false/FALSE -> 'N' (defaults to 'Y' on create if null)
        String dbActive = parseActiveFlag(requestDto.active(), "Y");

        IdType entity = IdType.builder()
                .idTyp(normalizedKey)
                .regex(requestDto.regex())
                .active(dbActive)
                .build();

        IdType savedEntity = idTypeRepo.save(entity);
        return IdTypeResp.fromEntity(savedEntity);
    }

    @Override
    @Transactional
    public IdTypeResp patchIdType(String idTyp, IdTypeReq requestDto) {
        String normalizedKey = idTyp != null ? idTyp.toUpperCase() : "";
        log.debug("Patching identity type: {}", normalizedKey);

        IdType existingEntity = idTypeRepo.findById(normalizedKey)
                .orElseThrow(() -> new IllegalArgumentException("Identity type not found: " + normalizedKey));

        if (requestDto.regex() != null) {
            existingEntity.setRegex(requestDto.regex());
        }

        // Only parse and update active if provided in the patch payload
        if (requestDto.active() != null) {
            existingEntity.setActive(parseActiveFlag(requestDto.active(), existingEntity.getActive()));
        }

        IdType updatedEntity = idTypeRepo.save(existingEntity);
        return IdTypeResp.fromEntity(updatedEntity);
    }

    @Override
    @Transactional
    public void deleteIdType(String idTyp) {
        log.debug("Deleting identity type: {}", idTyp);
        if (!idTypeRepo.existsById(idTyp)) {
            throw new IllegalArgumentException("Identity type not found: " + idTyp);
        }
        idTypeRepo.deleteById(idTyp);
    }

    private String parseActiveFlag(String activeInput, String defaultValue) {
        if (activeInput == null) {
            return defaultValue;
        }

        String upper = activeInput.toUpperCase();
        if (upper.equals("Y") || upper.equals("TRUE")) {
            return "Y";
        } else if (upper.equals("N") || upper.equals("FALSE")) {
            return "N";
        }

        throw new IllegalArgumentException("Invalid active flag value: " + activeInput);
    }

}