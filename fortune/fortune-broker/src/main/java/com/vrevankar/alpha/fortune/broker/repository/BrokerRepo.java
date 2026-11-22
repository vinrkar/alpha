package com.vrevankar.alpha.fortune.broker.repository;

import com.vrevankar.alpha.fortune.broker.entity.Broker;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface BrokerRepo extends JpaRepository<Broker, Long> {
}