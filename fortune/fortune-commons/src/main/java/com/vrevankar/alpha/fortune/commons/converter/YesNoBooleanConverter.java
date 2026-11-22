package com.vrevankar.alpha.fortune.commons.converter;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter
public class YesNoBooleanConverter implements AttributeConverter<Boolean, String> {

    @Override
    public String convertToDatabaseColumn(Boolean attribute) {
        return Boolean.TRUE.equals(attribute) ? "Y" : "N";
    }

    @Override
    public Boolean convertToEntityAttribute(String dbData) {
        return parse(dbData);
    }

    public static Boolean parse(String val) {
        return val != null && ("Y".equalsIgnoreCase(val.trim()) || "TRUE".equalsIgnoreCase(val.trim()));
    }
}