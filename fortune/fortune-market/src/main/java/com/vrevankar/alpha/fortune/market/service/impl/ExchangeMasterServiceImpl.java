package com.vrevankar.alpha.fortune.market.service.impl;

import com.vrevankar.alpha.fortune.market.domain.dto.req.ExchangeMasterReq;
import com.vrevankar.alpha.fortune.market.domain.dto.resp.ExchangeMasterResp;
import com.vrevankar.alpha.fortune.market.domain.entity.ExchangeMaster;
import com.vrevankar.alpha.fortune.market.repository.ExchangeMasterRepo;
import com.vrevankar.alpha.fortune.market.service.ExchangeMasterService;
import jakarta.persistence.EntityManager;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

@Slf4j
@Service
@RequiredArgsConstructor
class ExchangeMasterServiceImpl implements ExchangeMasterService {

    private final ExchangeMasterRepo exchangeMasterRepo;
    private final EntityManager entityManager;

    @Override
    @Transactional
    public List<ExchangeMasterResp> onboardExchanges(List<ExchangeMasterReq> requests) {
        List<ExchangeMasterResp> responses = new ArrayList<>();

        for (ExchangeMasterReq req : requests) {
            try {
                ExchangeMaster entity = exchangeMasterRepo
                        .findByFrCurrAndToCurr(req.frCurr(), req.toCurr())
                        .map(existing -> {
                            existing.setActive("Y");
                            return existing;
                        })
                        .orElseGet(() -> ExchangeMaster.builder()
                                .frCurr(req.frCurr())
                                .toCurr(req.toCurr())
                                .active("Y")
                                .build());

                ExchangeMaster saved = exchangeMasterRepo.save(entity);
                responses.add(mapToResp(saved));
            } catch (Exception e) {
                log.error("Failed to onboard currency pair {}/{}", req.frCurr(), req.toCurr(), e);
                responses.add(new ExchangeMasterResp(null, req.frCurr(), req.toCurr(), "N", null, null, "FAILED"));
            }
        }
        return responses;
    }

    @Override
    @Transactional
    public ExchangeMasterResp patchExchange(Long xchgId, ExchangeMasterReq request) {
        ExchangeMaster entity = exchangeMasterRepo.findById(xchgId)
                .orElseThrow(() -> new IllegalArgumentException("Exchange rate pair not found with ID: " + xchgId));

        boolean isChanged = false;
        isChanged |= updateIfChanged(request.frCurr(), entity.getFrCurr(), entity::setFrCurr);
        isChanged |= updateIfChanged(request.toCurr(), entity.getToCurr(), entity::setToCurr);
        isChanged |= updateIfChanged(request.active(), entity.getActive(), entity::setActive);

        if (!isChanged) {
            return mapToResp(entity);
        }

        ExchangeMaster updated = exchangeMasterRepo.saveAndFlush(entity);
        entityManager.refresh(updated);

        return mapToResp(updated);
    }

    @Override
    @Transactional(readOnly = true)
    public ExchangeMasterResp getExchangeById(Long xchgId) {
        return exchangeMasterRepo.findById(xchgId)
                .map(entity -> mapToResp(entity, new String[] { null }))
                .orElseThrow(() -> new IllegalArgumentException("Exchange rate pair not found with ID: " + xchgId));
    }

    @Override
    @Transactional(readOnly = true)
    public List<ExchangeMasterResp> getAllExchanges() {
        return exchangeMasterRepo.findAll().stream()
                .map(entity -> mapToResp(entity, new String[] { null }))
                .toList();
    }

    private ExchangeMasterResp mapToResp(ExchangeMaster entity, String... status) {
        return new ExchangeMasterResp(
                entity.getXchgId(),
                entity.getFrCurr(),
                entity.getToCurr(),
                entity.getActive(),
                entity.getCrtDttm(),
                entity.getUpdtDttm(),
                status.length == 0 ? "COMPLETED" : status[0]
        );
    }

    private <T> boolean updateIfChanged(T newValue, T currentValue, Consumer<T> setter) {
        if (newValue != null && !newValue.equals(currentValue)) {
            setter.accept(newValue);
            return true;
        }
        return false;
    }
}