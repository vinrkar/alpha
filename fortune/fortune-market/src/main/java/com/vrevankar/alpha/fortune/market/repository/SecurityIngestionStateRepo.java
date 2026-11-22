package com.vrevankar.alpha.fortune.market.repository;

import com.vrevankar.alpha.fortune.market.domain.entity.SecurityIngestionState;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SecurityIngestionStateRepo extends JpaRepository<SecurityIngestionState, String> {
}