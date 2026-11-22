package com.vrevankar.alpha.fortune.client.repository;

import com.vrevankar.alpha.fortune.client.entity.Client;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface ClientRepo extends JpaRepository<Client, UUID> {
    boolean existsByDpIdAndClientCd(String dpId, String clientCd);
    boolean existsByDpIdAndTradeCd(String dpId, String tradeCd);
}