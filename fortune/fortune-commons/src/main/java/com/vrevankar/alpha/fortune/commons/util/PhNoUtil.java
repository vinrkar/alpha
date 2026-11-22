package com.vrevankar.alpha.fortune.commons.util;

import com.google.i18n.phonenumbers.NumberParseException;
import com.google.i18n.phonenumbers.PhoneNumberUtil;
import com.google.i18n.phonenumbers.Phonenumber;

public class PhNoUtil {

    public static void validatePhoneCountryMatch(String isoCd, String phNo) {
        if (isoCd == null || isoCd.isBlank() || phNo == null || phNo.isBlank()) {
            throw new IllegalArgumentException("ISO code and phone number must not be null or blank.");
        }

        try {
            PhoneNumberUtil phoneUtil = PhoneNumberUtil.getInstance();

            // 1. Parse the incoming phone number string
            Phonenumber.PhoneNumber parsedPhone = phoneUtil.parse(phNo, null);
            int actualCountryCode = parsedPhone.getCountryCode();

            // 2. Extract the 2-letter region/country code from ISO string (e.g., "IN-MH" -> "IN")
            String regionCode = isoCd.split("-")[0].toUpperCase();

            // 3. Dynamically fetch the expected country code from libphonenumber metadata
            int expectedCountryCode = phoneUtil.getCountryCodeForRegion(regionCode);

            if (expectedCountryCode == 0) {
                throw new IllegalArgumentException("Invalid or unsupported ISO region code: " + regionCode);
            }

            // 4. Validate that they match
            if (actualCountryCode != expectedCountryCode) {
                throw new IllegalArgumentException(String.format(
                        "Phone number country code (+%d) does not match the address ISO region '%s' (expected +%d).",
                        actualCountryCode, isoCd, expectedCountryCode
                ));
            }
        } catch (NumberParseException e) {
            throw new IllegalArgumentException("Invalid phone number format provided: " + phNo);
        }
    }
}