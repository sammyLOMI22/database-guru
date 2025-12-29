"""Quality profile system for controlling speed vs accuracy tradeoffs.

This module provides a QualityProfile dataclass and factory function that
translates the user's quality slider setting (0-100) into concrete configuration
parameters for SQL generation, query planning, and error correction.

Quality Levels:
- FAST (0-30%): Minimal planning, 1 retry, skip verification
- BALANCED (31-70%): Standard planning, location hints enabled, 3 retries
- THOROUGH (71-100%): Force planning, tool exploration, 5 retries
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Quality level enum for categorizing slider value"""
    FAST = "fast"           # 0-30%
    BALANCED = "balanced"   # 31-70%
    THOROUGH = "thorough"   # 71-100%


@dataclass
class QualityProfile:
    """Configuration profile based on quality slider value.

    This dataclass holds all the configuration parameters that vary
    based on the user's quality preference. It's passed through the
    agent chain to control behavior at each stage.

    Attributes:
        level: The quality level category (FAST/BALANCED/THOROUGH)
        raw_value: The original slider value (0-100)

        # Planning Control
        force_planning: If True, always use query planning regardless of complexity
        complexity_threshold: Minimum complexity score to trigger planning (0.0-1.0)

        # LLM Generation
        temperature: LLM temperature for SQL generation
        use_enhanced_few_shot: Include location-aware examples in prompts
        include_location_hints: Call LocationMapper to enhance queries
        include_join_examples: Include JOIN pattern examples

        # Schema Context
        schema_sample_limit: Maximum sample values per column (0 = disabled)
        emphasize_samples: Use IMPORTANT markers for sample values

        # Correction Behavior
        use_parallel_corrections: Enable parallel correction attempts
        correction_timeout: Timeout for correction attempts (seconds)
        max_retries: Maximum retry attempts on error

        # Verification
        enable_result_verification: Validate results for logical correctness

        # Tools
        enable_tool_exploration: Use tools to explore schema before SQL generation

        # Pre-Generation Semantic Understanding (NEW)
        enable_intent_classification: Classify query intent before SQL generation
        enable_pre_validation: Validate schema can satisfy query before LLM call
        use_dynamic_examples: Generate schema-specific few-shot examples
    """
    level: QualityLevel
    raw_value: int

    # Planning Control
    force_planning: bool
    complexity_threshold: float

    # LLM Generation
    temperature: float
    use_enhanced_few_shot: bool
    include_location_hints: bool
    include_join_examples: bool

    # Schema Context
    schema_sample_limit: int
    emphasize_samples: bool

    # Correction Behavior
    use_parallel_corrections: bool
    correction_timeout: int
    max_retries: int

    # Verification
    enable_result_verification: bool

    # Tools
    enable_tool_exploration: bool

    # Pre-Generation Semantic Understanding (Phase 1 & 2)
    enable_intent_classification: bool
    enable_pre_validation: bool
    use_dynamic_examples: bool

    # Post-Generation Semantic Validation (Phase 3)
    enable_semantic_validation: bool

    def __str__(self) -> str:
        return f"QualityProfile({self.level.value}, {self.raw_value}%)"

    def __repr__(self) -> str:
        return (
            f"QualityProfile(level={self.level.value}, raw_value={self.raw_value}, "
            f"retries={self.max_retries}, location_hints={self.include_location_hints})"
        )


def get_quality_profile(quality_level: int) -> QualityProfile:
    """Generate a quality profile from slider value (0-100).

    This factory function translates the user's quality slider setting
    into a concrete QualityProfile with appropriate parameters for
    each quality tier.

    Args:
        quality_level: Integer 0-100 from settings (query_quality_level)

    Returns:
        QualityProfile with settings appropriate for the level

    Examples:
        >>> profile = get_quality_profile(50)
        >>> profile.level
        QualityLevel.BALANCED
        >>> profile.include_location_hints
        True

        >>> profile = get_quality_profile(0)
        >>> profile.level
        QualityLevel.FAST
        >>> profile.max_retries
        1
    """
    # Clamp to valid range
    quality_level = max(0, min(100, quality_level))

    if quality_level <= 30:
        # FAST: Speed over accuracy
        logger.debug(f"Creating FAST quality profile (level={quality_level})")
        return QualityProfile(
            level=QualityLevel.FAST,
            raw_value=quality_level,
            # Planning - minimal
            force_planning=False,
            complexity_threshold=0.8,  # Only plan very complex queries
            # LLM Generation - basic
            temperature=0.1,
            use_enhanced_few_shot=False,
            include_location_hints=False,
            include_join_examples=False,
            # Schema Context - none
            schema_sample_limit=0,
            emphasize_samples=False,
            # Corrections - minimal
            use_parallel_corrections=True,
            correction_timeout=5,
            max_retries=1,
            # Verification - skip
            enable_result_verification=False,
            # Tools - disabled
            enable_tool_exploration=False,
            # Pre-Generation - disabled for speed
            enable_intent_classification=False,
            enable_pre_validation=False,
            use_dynamic_examples=False,
            # Post-Generation - disabled for speed
            enable_semantic_validation=False,
        )
    elif quality_level <= 70:
        # BALANCED: Good accuracy with reasonable speed
        logger.debug(f"Creating BALANCED quality profile (level={quality_level})")
        return QualityProfile(
            level=QualityLevel.BALANCED,
            raw_value=quality_level,
            # Planning - standard
            force_planning=False,
            complexity_threshold=0.5,  # Current default threshold
            # LLM Generation - enhanced (BUG FIXES)
            temperature=0.1,
            use_enhanced_few_shot=True,
            include_location_hints=True,   # BUG FIX: Wire up LocationMapper
            include_join_examples=True,    # BUG FIX: Include JOIN examples
            # Schema Context - moderate
            schema_sample_limit=5,
            emphasize_samples=False,
            # Corrections - standard
            use_parallel_corrections=True,
            correction_timeout=10,
            max_retries=3,
            # Verification - enabled
            enable_result_verification=True,
            # Tools - disabled for speed
            enable_tool_exploration=False,
            # Pre-Generation - enabled for better accuracy
            enable_intent_classification=True,
            enable_pre_validation=True,
            use_dynamic_examples=True,
            # Post-Generation - enabled for validation
            enable_semantic_validation=True,
        )
    else:
        # THOROUGH: Maximum accuracy
        logger.debug(f"Creating THOROUGH quality profile (level={quality_level})")
        return QualityProfile(
            level=QualityLevel.THOROUGH,
            raw_value=quality_level,
            # Planning - aggressive
            force_planning=True,  # Always plan
            complexity_threshold=0.2,  # Plan even simple queries
            # LLM Generation - maximum context
            temperature=0.05,  # More deterministic
            use_enhanced_few_shot=True,
            include_location_hints=True,
            include_join_examples=True,
            # Schema Context - maximum
            schema_sample_limit=10,
            emphasize_samples=True,  # ** IMPORTANT ** markers
            # Corrections - aggressive
            use_parallel_corrections=True,
            correction_timeout=15,
            max_retries=5,
            # Verification - always
            enable_result_verification=True,
            # Tools - enabled for exploration
            enable_tool_exploration=True,
            # Pre-Generation - enabled for maximum accuracy
            enable_intent_classification=True,
            enable_pre_validation=True,
            use_dynamic_examples=True,
            # Post-Generation - enabled for validation
            enable_semantic_validation=True,
        )


def get_quality_profile_with_settings(
    quality_level: int,
    system_settings: dict = None
) -> "QualityProfile":
    """Generate a quality profile with optional system settings overrides.

    This allows users to explicitly enable/disable semantic understanding
    features through the settings UI, overriding the quality-tier defaults.

    Args:
        quality_level: Integer 0-100 from settings (query_quality_level)
        system_settings: Optional dict with keys like 'enable_intent_classification',
                        'enable_dynamic_examples', 'enable_semantic_validation'

    Returns:
        QualityProfile with settings merged from quality level and overrides
    """
    # Start with the base profile from quality level
    profile = get_quality_profile(quality_level)

    # Override with explicit user settings if provided
    if system_settings:
        if system_settings.get('enable_intent_classification') is not None:
            profile = QualityProfile(
                **{**profile.__dict__, 'enable_intent_classification': system_settings['enable_intent_classification']}
            )
        if system_settings.get('enable_dynamic_examples') is not None:
            profile = QualityProfile(
                **{**profile.__dict__, 'use_dynamic_examples': system_settings['enable_dynamic_examples']}
            )
        if system_settings.get('enable_semantic_validation') is not None:
            profile = QualityProfile(
                **{**profile.__dict__, 'enable_semantic_validation': system_settings['enable_semantic_validation']}
            )

    return profile


def get_quality_level_description(quality_level: int) -> str:
    """Get a human-readable description of the quality level.

    Args:
        quality_level: Integer 0-100

    Returns:
        Description string for UI display
    """
    if quality_level <= 30:
        return "Fast: Quick responses, minimal planning. Best for simple queries."
    elif quality_level <= 70:
        return "Balanced: Standard planning and verification. Recommended for most queries."
    else:
        return "Thorough: Full analysis, rich context. Best for complex queries."
