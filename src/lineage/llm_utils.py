"""LLM Utility Functions for Lineage Intelligence

Shared utilities for LLM response parsing used across lineage agents.
"""

import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def extract_json_object(text: str) -> Optional[str]:
    """
    Extract a valid JSON object from LLM response text using balanced brace matching.

    This is more robust than simple find/rfind as it handles nested objects
    and multiple JSON objects in the response. It also handles cases where
    the LLM includes explanatory text before/after the JSON.

    Args:
        text: Raw LLM response text that may contain JSON

    Returns:
        The extracted JSON string if valid, None otherwise

    Example:
        >>> text = "Here is the analysis:\\n{\"summary\": \"test\", \"score\": 0.8}"
        >>> extract_json_object(text)
        '{"summary": "test", "score": 0.8}'
    """
    # Find the first opening brace
    start = text.find("{")
    if start == -1:
        return None

    # Count braces to find the matching closing brace
    brace_count = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_str = text[start:i + 1]
                # Validate it's actually valid JSON
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    # This block wasn't valid JSON, continue searching
                    continue

    # If we get here, try the simple approach as fallback
    end = text.rfind("}") + 1
    if end > start:
        fallback = text[start:end]
        try:
            json.loads(fallback)
            return fallback
        except json.JSONDecodeError:
            pass

    return None


def parse_json_response(text: str, fallback: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Extract and parse a JSON object from LLM response text.

    Combines extract_json_object with JSON parsing for convenience.

    Args:
        text: Raw LLM response text
        fallback: Optional fallback dict to return on failure

    Returns:
        Parsed JSON as dict, or fallback if parsing fails
    """
    json_str = extract_json_object(text)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse error after extraction: {e}")

    return fallback
