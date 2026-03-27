"""Module for AI agent governance, simplified to PII (Personally Identifiable Information) protection."""

import datetime
import json
import os
from src.pii import mask_pii

# Governance simplified to PII protection only based on user feedback
AUDIT_LOG_PATH = "logs/governance_audit.log"

def log_event(event_type: str, details: dict):
    """Logs a governance event to the audit file."""
    timestamp = datetime.datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "details": details
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def validate_input(prompt: str) -> tuple[bool, str | None, str]:
    """
    Masks PII in user input. Always returns is_valid=True for non-PII content.
    Returns (is_valid, reason, masked_prompt).
    """
    if not prompt:
        return True, None, prompt

    # 1. Mask PII in input
    masked_prompt = mask_pii(prompt)
    if masked_prompt != prompt:
        log_event("input_modification", {"type": "pii_masking"})
        # We still return True but with the masked prompt
    
    return True, None, masked_prompt

def validate_output(response: str) -> tuple[str, list[str]]:
    """
    Masks PII in agent output. 
    Returns (cleaned_response, list_of_violations).
    """
    violations = []
    
    # 1. Mask PII 
    cleaned_response = mask_pii(response)
    if cleaned_response != response:
        violations.append("PII Masked")
        log_event("output_modification", {"type": "pii_masking"})

    return cleaned_response, violations
