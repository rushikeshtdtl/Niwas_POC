package com.niwas.kyc.repository;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import com.niwas.kyc.model.User;

public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByPhone(String phone);      // ✅ matches 'phone' field in User

    Optional<User> findByEmail(String email);      // ✅ matches 'email' field in User

    boolean existsByPhone(String phone);

    boolean existsByEmail(String email);
}