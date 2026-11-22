package com.vrevankar.alpha.fortune.client.repository;

import com.vrevankar.alpha.fortune.client.entity.IdType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface IdTypeRepo extends JpaRepository<IdType, String> {
    List<IdType> findByActive(String active);
}