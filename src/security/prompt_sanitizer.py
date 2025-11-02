"""Prompt sanitization utilities to prevent prompt injection attacks"""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum lengths to prevent token overflow
MAX_QUESTION_LENGTH = 500  # characters
MAX_CONTEXT_PROMPT_LENGTH = 8000  # characters (~2000 tokens)
MAX_SQL_LENGTH = 2000  # characters for historical SQL in context

# Patterns that indicate potential prompt injection attempts
INJECTION_PATTERNS = [
    # Direct instruction injection
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(all\s+)?(previous|prior|above|everything)",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",

    # Role manipulation
    r"you\s+are\s+now\s+(a|an)\s+\w+",
    r"act\s+as\s+(a|an)\s+\w+",
    r"pretend\s+to\s+be\s+(a|an)\s+\w+",

    # System/instruction manipulation
    r"system\s*:",
    r"<\s*system\s*>",
    r"new\s+instructions?",
    r"override\s+instructions?",

    # Delimiter injection attempts
    r"---+\s*$",  # Multiple dashes at end (trying to close sections)
    r"={3,}",  # Multiple equals signs
    r"\*{3,}",  # Multiple asterisks
]

# Compile patterns for performance
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS]


def sanitize_user_input(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize user input to prevent prompt injection

    Args:
        text: User input text
        max_length: Maximum allowed length (default: MAX_QUESTION_LENGTH)

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    if max_length is None:
        max_length = MAX_QUESTION_LENGTH

    # Truncate if too long
    if len(text) > max_length:
        logger.warning(f"Input truncated from {len(text)} to {max_length} characters")
        text = text[:max_length]

    # Remove null bytes and other control characters except newline/tab
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

    # Normalize whitespace (replace multiple spaces with single space)
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def detect_injection_attempt(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detect potential prompt injection attempts

    Args:
        text: Text to analyze

    Returns:
        Tuple of (is_suspicious, reason)
    """
    text_lower = text.lower()

    # Check against known injection patterns
    for i, pattern in enumerate(COMPILED_PATTERNS):
        if pattern.search(text_lower):
            reason = f"Potential injection pattern detected: {INJECTION_PATTERNS[i]}"
            logger.warning(f"Injection attempt detected: {reason}")
            return True, reason

    # Check for excessive delimiter usage
    if text.count('---') > 1:
        return True, "Excessive delimiter usage detected"

    if text.count('\n') > 10:
        return True, "Excessive newlines detected"

    # Check for multiple consecutive special characters (potential delimiter injection)
    if re.search(r'[=*#-]{5,}', text):
        return True, "Suspicious delimiter pattern detected"

    return False, None


def sanitize_for_context(text: str, field_name: str = "text") -> str:
    """
    Sanitize text for inclusion in conversation context

    This is more permissive than sanitize_user_input since it may include
    legitimate SQL or system messages, but still protects against injection.

    Args:
        text: Text to sanitize
        field_name: Name of field (for logging)

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Apply appropriate length limit based on field type
    max_length = MAX_SQL_LENGTH if field_name == "sql" else MAX_QUESTION_LENGTH

    # Truncate if too long
    if len(text) > max_length:
        logger.info(f"{field_name} truncated from {len(text)} to {max_length} chars")
        text = text[:max_length] + "... [truncated]"

    # Remove null bytes and dangerous control characters
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

    # Escape potential delimiter injection by adding space after dashes
    # This breaks attempts to inject "---" delimiters
    text = re.sub(r'(-{3,})', r'\1 ', text)

    return text.strip()


def validate_context_prompt_length(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that context prompt doesn't exceed token limits

    Args:
        prompt: Full context prompt

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(prompt) > MAX_CONTEXT_PROMPT_LENGTH:
        return False, f"Context prompt too long: {len(prompt)} chars (max: {MAX_CONTEXT_PROMPT_LENGTH})"

    # Rough token estimation (1 token ≈ 4 characters for English)
    estimated_tokens = len(prompt) // 4
    max_tokens = 2000  # Safe limit for most LLMs

    if estimated_tokens > max_tokens:
        return False, f"Estimated {estimated_tokens} tokens exceeds limit of {max_tokens}"

    return True, None


def sanitize_question_for_prompt(question: str) -> str:
    """
    Sanitize user question before including in LLM prompt

    This applies strict sanitization and injection detection.

    Args:
        question: User's question

    Returns:
        Sanitized question

    Raises:
        ValueError: If injection attempt is detected
    """
    # First, basic sanitization
    sanitized = sanitize_user_input(question)

    # Detect injection attempts
    is_suspicious, reason = detect_injection_attempt(sanitized)

    if is_suspicious:
        logger.warning(f"Suspicious input detected: {reason}")
        # Don't raise exception - just log and sanitize more aggressively
        # Remove the suspicious parts by keeping only alphanumeric, spaces, and basic punctuation
        sanitized = re.sub(r'[^a-zA-Z0-9\s,.?!-]', ' ', sanitized)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        logger.info(f"Sanitized suspicious input to: {sanitized}")

    return sanitized


def create_safe_context_prompt(
    question: str,
    context_messages: list,
    max_context_size: int = 3
) -> str:
    """
    Create a safe context-aware prompt with proper delimiters and sanitization

    Args:
        question: Current user question
        context_messages: List of previous messages
        max_context_size: Maximum number of context messages to include

    Returns:
        Sanitized and structured prompt

    Raises:
        ValueError: If prompt exceeds safe length limits
    """
    # Sanitize the current question
    safe_question = sanitize_question_for_prompt(question)

    # Build context with clear, injection-resistant delimiters
    prompt_parts = []

    # Use XML-like tags that are harder to inject naturally
    prompt_parts.append("<conversation_history>")

    # Limit context size
    messages_to_include = context_messages[-max_context_size:] if context_messages else []

    for i, msg in enumerate(messages_to_include, 1):
        prompt_parts.append(f"<query id=\"{i}\">")

        # Sanitize each field
        question_text = sanitize_for_context(
            msg.get('question', ''),
            field_name="question"
        )
        prompt_parts.append(f"  <question>{question_text}</question>")

        if msg.get('sql'):
            sql_text = sanitize_for_context(
                msg.get('sql', ''),
                field_name="sql"
            )
            prompt_parts.append(f"  <sql>{sql_text}</sql>")

        if msg.get('success'):
            result_count = msg.get('result_count', 0)
            prompt_parts.append(f"  <result>Success ({result_count} rows)</result>")
        elif msg.get('executed'):
            prompt_parts.append(f"  <result>Error</result>")

        prompt_parts.append("</query>")

    prompt_parts.append("</conversation_history>")
    prompt_parts.append("")
    prompt_parts.append("<current_query>")
    prompt_parts.append(f"<question>{safe_question}</question>")
    prompt_parts.append("</current_query>")
    prompt_parts.append("")
    prompt_parts.append("<instructions>")
    prompt_parts.append("- If the current question refers to a previous query, modify the most recent SQL accordingly")
    prompt_parts.append("- If the current question is standalone, generate a new query from scratch")
    prompt_parts.append("- Use the conversation history to understand context and user intent")
    prompt_parts.append("- IMPORTANT: Only generate valid SQL queries based on the database schema")
    prompt_parts.append("</instructions>")

    # Join and validate length
    full_prompt = "\n".join(prompt_parts)

    is_valid, error = validate_context_prompt_length(full_prompt)
    if not is_valid:
        logger.error(f"Context prompt validation failed: {error}")
        # Truncate context if too long
        if len(messages_to_include) > 1:
            # Retry with fewer messages
            return create_safe_context_prompt(
                question,
                context_messages,
                max_context_size=max_context_size - 1
            )
        else:
            # If still too long with just one message, truncate the prompt
            full_prompt = full_prompt[:MAX_CONTEXT_PROMPT_LENGTH]

    return full_prompt
