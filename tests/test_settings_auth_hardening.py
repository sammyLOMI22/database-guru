"""Tests for Settings.check_auth_hardening (Phase 24.7 follow-up).

The validator runs at startup. These tests confirm typo'd flag values fail
fast (rather than silently falling back at request time) and that valid
combinations pass cleanly.
"""
import pytest

from src.config.settings import Settings


def _make(**overrides) -> Settings:
    base = dict(JWT_SECRET="x" * 32)
    base.update(overrides)
    return Settings(**base)


class TestCheckAuthHardening:
    def test_defaults_pass(self):
        _make().check_auth_hardening()

    def test_invalid_reset_mode_raises(self):
        s = _make(AUTH_PASSWORD_RESET_MODE="token")
        with pytest.raises(ValueError, match="AUTH_PASSWORD_RESET_MODE"):
            s.check_auth_hardening()

    def test_negative_history_depth_raises(self):
        s = _make(AUTH_PASSWORD_HISTORY_DEPTH=-1)
        with pytest.raises(ValueError, match="AUTH_PASSWORD_HISTORY_DEPTH"):
            s.check_auth_hardening()

    def test_zero_lockout_threshold_raises(self):
        s = _make(AUTH_LOGIN_LOCKOUT_THRESHOLD=0)
        with pytest.raises(ValueError, match="AUTH_LOGIN_LOCKOUT_THRESHOLD"):
            s.check_auth_hardening()

    def test_zero_change_password_rate_raises(self):
        s = _make(AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE=0)
        with pytest.raises(ValueError, match="AUTH_CHANGE_PASSWORD_PER_USER_PER_MINUTE"):
            s.check_auth_hardening()

    def test_reset_token_without_base_url_warns_but_passes(self, caplog):
        s = _make(AUTH_PASSWORD_RESET_MODE="reset_token", AUTH_PASSWORD_RESET_BASE_URL="")
        with caplog.at_level("WARNING"):
            s.check_auth_hardening()  # does not raise
        assert any("AUTH_PASSWORD_RESET_BASE_URL" in r.message for r in caplog.records)

    def test_reset_token_with_base_url_silent(self, caplog):
        s = _make(
            AUTH_PASSWORD_RESET_MODE="reset_token",
            AUTH_PASSWORD_RESET_BASE_URL="http://localhost:3000",
        )
        with caplog.at_level("WARNING"):
            s.check_auth_hardening()
        assert not any("AUTH_PASSWORD_RESET_BASE_URL" in r.message for r in caplog.records)
