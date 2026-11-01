import pytest
from unittest.mock import MagicMock
from providers.gemini_rotator import GeminiKeyRotator, DEFAULT_KEYS


def test_rotator_initialization():
    rotator = GeminiKeyRotator()
    assert rotator.total_keys == len(DEFAULT_KEYS)
    assert rotator.get_current_key() == DEFAULT_KEYS[0]


def test_rotator_switch_keys():
    rotator = GeminiKeyRotator(keys=["KEY_1", "KEY_2", "KEY_3"])
    assert rotator.get_current_key() == "KEY_1"
    
    next_key = rotator.rotate_to_next(reason="quota")
    assert next_key == "KEY_2"
    assert rotator.get_current_key() == "KEY_2"
    
    rotator.rotate_to_next(reason="quota")
    assert rotator.get_current_key() == "KEY_3"
    
    # Cycles back to KEY_1
    rotator.rotate_to_next(reason="cycle")
    assert rotator.get_current_key() == "KEY_1"


def test_rotator_quota_detection():
    rotator = GeminiKeyRotator()
    assert rotator.is_quota_or_rate_limit_error(Exception("429 Resource has been exhausted (e.g. check quota)."))
    assert rotator.is_quota_or_rate_limit_error(Exception("RESOURCE_EXHAUSTED: Rate limit exceeded"))
    assert rotator.is_quota_or_rate_limit_error(Exception("quota exceeded for quota metric"))
    assert not rotator.is_quota_or_rate_limit_error(ValueError("Invalid syntax"))


def test_execute_with_rotation_retries_on_quota():
    rotator = GeminiKeyRotator(keys=["KEY_A", "KEY_B", "KEY_C"])
    call_counts = {"count": 0}
    
    def fake_call(client):
        call_counts["count"] += 1
        if rotator.get_current_key() == "KEY_A":
            raise Exception("429 Resource has been exhausted")
        return "SUCCESS_WITH_" + rotator.get_current_key()
    
    result = rotator.execute_with_rotation(fake_call)
    assert result == "SUCCESS_WITH_KEY_B"
    assert call_counts["count"] == 2
    assert rotator.get_current_key() == "KEY_B"

