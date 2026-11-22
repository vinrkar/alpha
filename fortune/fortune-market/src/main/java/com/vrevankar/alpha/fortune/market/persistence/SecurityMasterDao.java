package com.vrevankar.alpha.fortune.market.persistence;

import com.vrevankar.alpha.fortune.market.domain.entity.SecurityMaster;
import com.vrevankar.alpha.fortune.market.repository.SecurityMasterRepo;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;

@Component
@RequiredArgsConstructor
public class SecurityMasterDao {

    private final SecurityMasterRepo repository;

    public SecurityMaster save(SecurityMaster entity) {
        return repository.save(entity);
    }

    public List<SecurityMaster> saveAll(List<SecurityMaster> entities) {
        return repository.saveAll(entities);
    }

    public Optional<SecurityMaster> findByIsin(String isin) {
        return repository.findByIsin(isin);
    }

    public List<SecurityMaster> findByStatus(String status, Pageable pageable) {
        return repository.findByStatus(status, pageable);
    }

    public List<SecurityMaster> findAll() {
        return repository.findAll();
    }

    public boolean existsByIsin(String isin) {
        return repository.existsByIsin(isin);
    }

    public void deleteByIsin(String isin) {
        repository.findByIsin(isin).ifPresent(repository::delete);
    }
}