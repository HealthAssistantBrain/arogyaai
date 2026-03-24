"""
Utility functions for ArogyaAI Backend.
"""

def safe_input(input_str: str, max_chars: int = 12000) -> str:
    """
    Sanitize input by truncating it to a safe maximum length.
    Prevents potential memory/processing issues with excessively large payloads.
    """
    if not input_str:
        return ""
    if len(input_str) > max_chars:
        return input_str[:max_chars]
    return input_str
