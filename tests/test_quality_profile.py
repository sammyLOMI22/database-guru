"""Tests for the quality profile system.

These tests verify the QualityProfile dataclass and get_quality_profile()
factory function work correctly across all quality levels.
"""
import pytest
from src.llm.quality_profile import (
    QualityProfile,
    QualityLevel,
    get_quality_profile,
    get_quality_level_description,
)


class TestQualityLevelEnum:
    """Tests for QualityLevel enum"""

    def test_fast_value(self):
        """Test FAST level value"""
        assert QualityLevel.FAST.value == "fast"

    def test_balanced_value(self):
        """Test BALANCED level value"""
        assert QualityLevel.BALANCED.value == "balanced"

    def test_thorough_value(self):
        """Test THOROUGH level value"""
        assert QualityLevel.THOROUGH.value == "thorough"


class TestQualityProfileDataclass:
    """Tests for QualityProfile dataclass"""

    def test_str_representation(self):
        """Test string representation"""
        profile = get_quality_profile(50)
        assert str(profile) == "QualityProfile(balanced, 50%)"

    def test_repr_representation(self):
        """Test repr representation"""
        profile = get_quality_profile(50)
        assert "level=balanced" in repr(profile)
        assert "raw_value=50" in repr(profile)


class TestGetQualityProfileFast:
    """Tests for FAST quality level (0-30%)"""

    def test_level_at_0(self):
        """Test 0% generates FAST profile"""
        profile = get_quality_profile(0)
        assert profile.level == QualityLevel.FAST
        assert profile.raw_value == 0

    def test_level_at_15(self):
        """Test 15% generates FAST profile"""
        profile = get_quality_profile(15)
        assert profile.level == QualityLevel.FAST

    def test_level_at_30(self):
        """Test 30% still generates FAST profile (boundary)"""
        profile = get_quality_profile(30)
        assert profile.level == QualityLevel.FAST

    def test_fast_retries(self):
        """Test FAST mode has minimal retries"""
        profile = get_quality_profile(0)
        assert profile.max_retries == 1

    def test_fast_no_location_hints(self):
        """Test FAST mode disables location hints"""
        profile = get_quality_profile(0)
        assert profile.include_location_hints is False

    def test_fast_no_verification(self):
        """Test FAST mode skips result verification"""
        profile = get_quality_profile(0)
        assert profile.enable_result_verification is False

    def test_fast_no_force_planning(self):
        """Test FAST mode doesn't force planning"""
        profile = get_quality_profile(0)
        assert profile.force_planning is False

    def test_fast_high_complexity_threshold(self):
        """Test FAST mode has high complexity threshold (only plan very complex)"""
        profile = get_quality_profile(0)
        assert profile.complexity_threshold == 0.8

    def test_fast_no_tool_exploration(self):
        """Test FAST mode disables tool exploration"""
        profile = get_quality_profile(0)
        assert profile.enable_tool_exploration is False


class TestGetQualityProfileBalanced:
    """Tests for BALANCED quality level (31-70%)"""

    def test_level_at_31(self):
        """Test 31% switches to BALANCED profile"""
        profile = get_quality_profile(31)
        assert profile.level == QualityLevel.BALANCED

    def test_level_at_50(self):
        """Test default 50% is BALANCED"""
        profile = get_quality_profile(50)
        assert profile.level == QualityLevel.BALANCED
        assert profile.raw_value == 50

    def test_level_at_70(self):
        """Test 70% still BALANCED (boundary)"""
        profile = get_quality_profile(70)
        assert profile.level == QualityLevel.BALANCED

    def test_balanced_retries(self):
        """Test BALANCED mode has standard retries"""
        profile = get_quality_profile(50)
        assert profile.max_retries == 3

    def test_balanced_location_hints_enabled(self):
        """Test BALANCED mode enables location hints (BUG FIX)"""
        profile = get_quality_profile(50)
        assert profile.include_location_hints is True

    def test_balanced_join_examples_enabled(self):
        """Test BALANCED mode enables JOIN examples (BUG FIX)"""
        profile = get_quality_profile(50)
        assert profile.include_join_examples is True

    def test_balanced_verification_enabled(self):
        """Test BALANCED mode enables result verification"""
        profile = get_quality_profile(50)
        assert profile.enable_result_verification is True

    def test_balanced_default_complexity_threshold(self):
        """Test BALANCED mode uses standard complexity threshold"""
        profile = get_quality_profile(50)
        assert profile.complexity_threshold == 0.5

    def test_balanced_no_force_planning(self):
        """Test BALANCED mode doesn't force planning"""
        profile = get_quality_profile(50)
        assert profile.force_planning is False

    def test_balanced_no_tool_exploration(self):
        """Test BALANCED mode disables tool exploration (for speed)"""
        profile = get_quality_profile(50)
        assert profile.enable_tool_exploration is False


class TestGetQualityProfileThorough:
    """Tests for THOROUGH quality level (71-100%)"""

    def test_level_at_71(self):
        """Test 71% switches to THOROUGH profile"""
        profile = get_quality_profile(71)
        assert profile.level == QualityLevel.THOROUGH

    def test_level_at_85(self):
        """Test 85% is THOROUGH"""
        profile = get_quality_profile(85)
        assert profile.level == QualityLevel.THOROUGH

    def test_level_at_100(self):
        """Test 100% is max THOROUGH"""
        profile = get_quality_profile(100)
        assert profile.level == QualityLevel.THOROUGH
        assert profile.raw_value == 100

    def test_thorough_retries(self):
        """Test THOROUGH mode has maximum retries"""
        profile = get_quality_profile(100)
        assert profile.max_retries == 5

    def test_thorough_force_planning(self):
        """Test THOROUGH mode forces planning"""
        profile = get_quality_profile(100)
        assert profile.force_planning is True

    def test_thorough_low_complexity_threshold(self):
        """Test THOROUGH mode has low complexity threshold (plan even simple)"""
        profile = get_quality_profile(100)
        assert profile.complexity_threshold == 0.2

    def test_thorough_tool_exploration_enabled(self):
        """Test THOROUGH mode enables tool exploration"""
        profile = get_quality_profile(100)
        assert profile.enable_tool_exploration is True

    def test_thorough_emphasize_samples(self):
        """Test THOROUGH mode emphasizes schema samples"""
        profile = get_quality_profile(100)
        assert profile.emphasize_samples is True

    def test_thorough_location_hints_enabled(self):
        """Test THOROUGH mode enables location hints"""
        profile = get_quality_profile(100)
        assert profile.include_location_hints is True


class TestValueClamping:
    """Tests for value clamping at boundaries"""

    def test_clamp_above_100(self):
        """Test values above 100 are clamped to 100"""
        profile = get_quality_profile(150)
        assert profile.raw_value == 100
        assert profile.level == QualityLevel.THOROUGH

    def test_clamp_below_0(self):
        """Test values below 0 are clamped to 0"""
        profile = get_quality_profile(-10)
        assert profile.raw_value == 0
        assert profile.level == QualityLevel.FAST

    def test_large_positive_value(self):
        """Test very large values are clamped"""
        profile = get_quality_profile(1000)
        assert profile.raw_value == 100
        assert profile.level == QualityLevel.THOROUGH

    def test_large_negative_value(self):
        """Test very negative values are clamped"""
        profile = get_quality_profile(-1000)
        assert profile.raw_value == 0
        assert profile.level == QualityLevel.FAST


class TestBoundaryTransitions:
    """Tests for exact boundary transitions"""

    def test_30_to_31_transition(self):
        """Test transition from FAST to BALANCED at 30->31"""
        profile_30 = get_quality_profile(30)
        profile_31 = get_quality_profile(31)

        assert profile_30.level == QualityLevel.FAST
        assert profile_31.level == QualityLevel.BALANCED

    def test_70_to_71_transition(self):
        """Test transition from BALANCED to THOROUGH at 70->71"""
        profile_70 = get_quality_profile(70)
        profile_71 = get_quality_profile(71)

        assert profile_70.level == QualityLevel.BALANCED
        assert profile_71.level == QualityLevel.THOROUGH


class TestQualityLevelDescription:
    """Tests for get_quality_level_description()"""

    def test_fast_description(self):
        """Test FAST level description"""
        desc = get_quality_level_description(15)
        assert "Fast" in desc
        assert "simple" in desc.lower()

    def test_balanced_description(self):
        """Test BALANCED level description"""
        desc = get_quality_level_description(50)
        assert "Balanced" in desc
        assert "Recommended" in desc

    def test_thorough_description(self):
        """Test THOROUGH level description"""
        desc = get_quality_level_description(85)
        assert "Thorough" in desc
        assert "complex" in desc.lower()


class TestProfileParameters:
    """Tests for specific parameter values"""

    def test_temperature_values(self):
        """Test temperature decreases with quality"""
        fast = get_quality_profile(0)
        balanced = get_quality_profile(50)
        thorough = get_quality_profile(100)

        assert fast.temperature == 0.1
        assert balanced.temperature == 0.1
        assert thorough.temperature == 0.05  # Most deterministic

    def test_correction_timeout_values(self):
        """Test correction timeout increases with quality"""
        fast = get_quality_profile(0)
        balanced = get_quality_profile(50)
        thorough = get_quality_profile(100)

        assert fast.correction_timeout == 5
        assert balanced.correction_timeout == 10
        assert thorough.correction_timeout == 15

    def test_schema_sample_limit_values(self):
        """Test schema sample limit increases with quality"""
        fast = get_quality_profile(0)
        balanced = get_quality_profile(50)
        thorough = get_quality_profile(100)

        assert fast.schema_sample_limit == 0
        assert balanced.schema_sample_limit == 5
        assert thorough.schema_sample_limit == 10
