package com.vrevankar.alpha.fortune.client.dto.req;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.vrevankar.alpha.fortune.client.validation.IdTypeGroups;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

@JsonIgnoreProperties(ignoreUnknown = false) // Forces failure on any unknown fields like "xyz"
public record IdTypeReq(
        @NotBlank(groups = IdTypeGroups.Create.class, message = "Identity type code cannot be blank")
        @Size(max = 30, message = "Identity type code must be at most 30 characters")
        String idTyp,

        @Size(
                max = 60,
                groups = {IdTypeGroups.Create.class, IdTypeGroups.Update.class},
                message = "Regex pattern must be at most 60 characters"
        )
        String regex,

        @Pattern(
                regexp = "^(?i)(Y|TRUE|N|FALSE)$",
                groups = {IdTypeGroups.Create.class, IdTypeGroups.Update.class},
                message = "Active must be one of: Y, y, true, TRUE, N, n, false, FALSE"
        )
        String active
) {}