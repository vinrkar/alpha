package com.vrevankar.alpha.fortune.client.dto.req;

import com.vrevankar.alpha.fortune.client.enums.AccountType;
import com.vrevankar.alpha.fortune.commons.dto.AddressReq;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.time.LocalDate;
import java.util.List;

public record ClientReq(

        @NotBlank(message = "DP ID is required")
        @Size(max = 8, message = "DP ID cannot exceed 8 characters")
        String dpId,

        @NotBlank(message = "Client Code is required")
        @Size(max = 8, message = "Client Code cannot exceed 8 characters")
        String clientCd,

        @NotBlank(message = "Trade Code is required")
        @Size(max = 8, message = "Trade Code cannot exceed 8 characters")
        String tradeCd,

        @NotBlank(message = "First name is required")
        @Size(max = 30, message = "First name cannot exceed 30 characters")
        String firstNm,

        @NotBlank(message = "Last name is required")
        @Size(max = 30, message = "Last name cannot exceed 30 characters")
        String lastNm,

        @NotBlank(message = "Phone number is required")
        @Size(max = 20, message = "Phone number cannot exceed 20 characters")
        String phNo,

        @NotBlank(message = "Email is required")
        @Email(message = "Email format is invalid")
        @Size(max = 60, message = "Email cannot exceed 60 characters")
        String email,

        @NotBlank(message = "Password is required")
        @Size(max = 50, message = "Password must not exceed 50 characters")
        String password,

        @NotNull(message = "Account type is required")
        AccountType accTyp,

        @Pattern(regexp = "^(?i:Y|N|TRUE|FALSE)$", message = "PIS must be Y, N, TRUE, or FALSE")
        String pis,

        @NotNull(message = "Account opening date is required")
        LocalDate accOpenDt,

        LocalDate accCloseDt,

        @NotNull(message = "Address details are required")
        @Valid
        AddressReq address,

        @NotEmpty(message = "At least one client identity is required")
        @Valid
        List<ClientIdentityReq> identities,

        @NotEmpty(message = "At least one wallet is required")
        @Valid
        List<WalletReq> wallets
) {}