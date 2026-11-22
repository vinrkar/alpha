package com.vrevankar.alpha.fortune.client.repository;

import com.vrevankar.alpha.fortune.client.entity.ClientIdentity;
import com.vrevankar.alpha.fortune.client.entity.ClientIdentityId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ClientIdentityRepo extends JpaRepository<ClientIdentity, ClientIdentityId> {

    // Fetch all identity records for a given client UUID
    List<ClientIdentity> findByClientId(UUID clientId);

    // Find an existing identity mapping by type and value (e.g., to resolve clientId for upsert)
    Optional<ClientIdentity> findByIdTypAndIdVal(String idTyp, String idVal);

    // Delete all identities associated with a client
    void deleteByClientId(UUID clientId);
}