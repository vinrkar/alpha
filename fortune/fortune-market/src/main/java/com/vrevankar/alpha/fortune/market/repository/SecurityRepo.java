package com.vrevankar.alpha.fortune.market.repository;

import com.vrevankar.alpha.fortune.market.domain.entity.Security;
import com.vrevankar.alpha.fortune.market.domain.entity.SecurityId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SecurityRepo extends JpaRepository<Security, SecurityId> {
}