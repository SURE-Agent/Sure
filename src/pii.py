"""Utility for PII (Personally Identifiable Information) masking using Regex and optionally Microsoft Presidio."""

import re
import streamlit as st

def mask_pii(text: str) -> str:
    """
    Detects and masks PII in the given text using Regex for common patterns.
    
    Entities handled: PHONE_NUMBER, CREDIT_CARD, EMAIL_ADDRESS.
    """
    if not text or not isinstance(text, str):
        return text

    # --- REGEX BASED MASKING (Fast and reliable) ---
    
    # Credit Cards (Various formats)
    cc_pattern = r'\b(?:\d[ -]*?){13,16}\b'
    text = re.sub(cc_pattern, "<TARJETA>", text)
    
    # Email Addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    text = re.sub(email_pattern, "<EMAIL>", text)
    
    # Phone Numbers (Common formats for Spain/International)
    # This pattern covers +34, 9 numbers, spaces/hyphens
    phone_pattern = r'\b(?:\+\d{1,3}[- ]?)?\(?\d{2,4}\)?[- ]?\d{2,4}[- ]?\d{2,4}\b'
    # Refined phone pattern to avoid matching small numbers
    text = re.sub(r'\b(?:\+\d{1,2}\s?)?\d{3}[\s.-]?\d{3}[\s.-]?\d{3,4}\b', "<TELÉFONO>", text)
    # Also catch common 9-digit numbers starting with 6, 7, 8, 9
    text = re.sub(r'\b[6789]\d{8}\b', "<TELÉFONO>", text)

    # Note: Addresses (LOCATION) and Names (PERSON) are much harder with regex
    # and usually require NLP models like Presidio + spaCy. 
    # For now, we focus on the most critical ones (Cards, Phones, Emails).

    return text

if __name__ == "__main__":
    # Simple test
    test_text = "Mi nombre es Juan Pérez, mi tarjeta es 4545-1234-5678-9012. Mi tel es 912345678. Contacto: juan.perez@example.com"
    print(f"Original: {test_text}")
    print(f"Masked:   {mask_pii(test_text)}")
