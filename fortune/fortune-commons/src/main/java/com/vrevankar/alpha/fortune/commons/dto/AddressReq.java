package com.vrevankar.alpha.fortune.commons.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record AddressReq(
        @NotBlank(message = "Street cannot be blank")
        @Size(max = 100, message = "Street cannot exceed 100 characters")
        String street,

        @NotBlank(message = "City cannot be blank")
        @Size(max = 30, message = "City cannot exceed 30 characters")
        String city,

        @NotBlank(message = "Pin cannot be blank")
        @Size(max = 6, message = "Pin cannot exceed 6 characters")
        String pin, // <-- Added Pin field

        @NotBlank(message = "ISO code cannot be blank")
        @Size(max = 6, message = "ISO code cannot exceed 6 characters")
        @Pattern(regexp = "^[A-Za-z]{2}-[A-Za-z0-9]{1,3}$", message = "ISO code must follow the ISO 3166-2 subdivision format (e.g., IN-MH, GB-ENG)")
        String isoCd,

        @NotBlank(message = "Phone number cannot be blank")
        @Size(max = 20, message = "Phone number cannot exceed 20 characters")
        String phNo,

        @NotBlank(message = "Email cannot be blank")
        @Email(message = "Invalid email format")
        @Size(max = 60, message = "Email cannot exceed 60 characters")
        String email
) {}