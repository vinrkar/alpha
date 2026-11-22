package com.vrevankar.alpha.fortune.commons.repository;

import com.vrevankar.alpha.fortune.commons.entity.Address;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface AddressRepo extends JpaRepository<Address, UUID> {
}