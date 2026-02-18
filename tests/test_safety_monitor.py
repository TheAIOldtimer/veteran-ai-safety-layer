"""
Tests for EnhancedSafetyMonitor
Part of the Veteran AI Safety Layer
https://github.com/TheAIOldtimer/veteran-ai-safety-layer

Run with:
    pytest tests/test_safety_monitor.py -v

Or with coverage:
    pytest tests/test_safety_monitor.py -v --cov=safety

These tests verify:
    - Critical, high, medium, and low risk detection fires correctly
    - Negation handling suppresses false positives
    - Context multipliers escalate risk appropriately
    - Emotional intensity escalates risk appropriately
    - Fail-safe returns HIGH risk on assessment error
    - Informal/abbreviation patterns are detected
    - Clean messages return NONE risk
"""

import pytest
import sys
import os

# Allow imports from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.safety_monitor import EnhancedSafetyMonitor, RiskLevel, InterventionType


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def monitor():
    """Fresh monitor instance for each test."""
    return EnhancedSafetyMonitor(user_id="test_user")


def make_emotional_context(intensity: float = 0.3, state: str = "neutral"):
    """Helper to build a minimal emotional context dict."""
    return {
        "emotional_intensity": intensity,
        "emotional_state": state,
        "primary_emotion": state,
    }


def assess(monitor, message, intensity=0.3, state="neutral", history=None):
    """Shorthand for running an assessment."""
    return monitor.assess_safety(
        message=message,
        emotional_context=make_emotional_context(intensity, state),
        emotional_history=history or []
    )


# =============================================================================
# CLEAN MESSAGES — should never trigger
# =============================================================================

class TestCleanMessages:

    def test_greeting(self, monitor):
        result = assess(monitor, "Hey, how are you?")
        assert result["risk_level"] == RiskLevel.NONE.value

    def test_casual_conversation(self, monitor):
        result = assess(monitor, "I had a really good day today, went for a walk.")
        assert result["risk_level"] == RiskLevel.NONE.value

    def test_talking_about_others(self, monitor):
        result = assess(monitor, "My mate said he wanted to die laughing at that film.")
        # "die" in context like this should not trigger — word boundary matters
        assert result["risk_level"] == RiskLevel.NONE.value

    def test_historical_reference(self, monitor):
        result = assess(monitor, "We studied suicide rates in the First World War.")
        assert result["risk_level"] == RiskLevel.NONE.value

    def test_tired_expression(self, monitor):
        result = assess(monitor, "I'm absolutely dead tired after that shift.")
        assert result["risk_level"] == RiskLevel.NONE.value


# =============================================================================
# CRITICAL RISK — must always fire
# =============================================================================

class TestCriticalRisk:

    def test_direct_suicide_statement(self, monitor):
        result = assess(monitor, "I'm going to kill myself tonight.")
        assert result["risk_level"] == RiskLevel.CRITICAL.value
        assert result["requires_intervention"] is True
        assert result["emergency_contact_suggested"] is True

    def test_end_my_life(self, monitor):
        result = assess(monitor, "I want to end my life.")
        assert result["risk_level"] == RiskLevel.CRITICAL.value

    def test_hanging(self, monitor):
        result = assess(monitor, "I've been thinking about hanging myself.")
        assert result["risk_level"] == RiskLevel.CRITICAL.value

    def test_goodbye_forever(self, monitor):
        result = assess(monitor, "This is goodbye forever. I mean it.")
        assert result["risk_level"] == RiskLevel.CRITICAL.value

    def test_informal_kms(self, monitor):
        result = assess(monitor, "I just want to kms")
        assert result["risk_level"] == RiskLevel.CRITICAL.value

    def test_top_myself(self, monitor):
        result = assess(monitor, "I'm going to top myself.")
        assert result["risk_level"] == RiskLevel.CRITICAL.value

    def test_intervention_type_is_emergency(self, monitor):
        result = assess(monitor, "I want to end my life.")
        assert result["intervention_type"] == InterventionType.EMERGENCY_RESOURCES.value

    def test_extra_whitespace_does_not_evade(self, monitor):
        result = assess(monitor, "I want to   kill   myself.")
        assert result["risk_level"] == RiskLevel.CRITICAL.value

    def test_mixed_case_does_not_evade(self, monitor):
        result = assess(monitor, "I Want To Kill Myself")
        assert result["risk_level"] == RiskLevel.CRITICAL.value


# =============================================================================
# HIGH RISK — must fire
# =============================================================================

class TestHighRisk:

    def test_no_reason_to_live(self, monitor):
        result = assess(monitor, "There's no reason to live anymore.")
        assert result["risk_level"] == RiskLevel.HIGH.value
        assert result["requires_intervention"] is True

    def test_world_better_without_me(self, monitor):
        result = assess(monitor, "Everyone would be better off without me.")
        assert result["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]

    def test_cant_go_on(self, monitor):
        result = assess(monitor, "I just can't go on like this.")
        assert result["risk_level"] == RiskLevel.HIGH.value

    def test_burden_statement(self, monitor):
        result = assess(monitor, "I'm just a burden on everyone around me.")
        assert result["risk_level"] == RiskLevel.HIGH.value

    def test_intervention_type_is_crisis(self, monitor):
        result = assess(monitor, "There's no reason to live anymore.")
        assert result["intervention_type"] in [
            InterventionType.CRISIS_RESPONSE.value,
            InterventionType.EMERGENCY_RESOURCES.value
        ]


# =============================================================================
# MEDIUM RISK — must fire
# =============================================================================

class TestMediumRisk:

    def test_self_harm(self, monitor):
        result = assess(monitor, "I've been cutting myself again.")
        assert result["risk_level"] == RiskLevel.MEDIUM.value
        assert result["requires_followup"] is True

    def test_hate_myself(self, monitor):
        result = assess(monitor, "I absolutely hate myself.")
        assert result["risk_level"] == RiskLevel.MEDIUM.value

    def test_worthless(self, monitor):
        result = assess(monitor, "I feel completely worthless.")
        assert result["risk_level"] == RiskLevel.MEDIUM.value

    def test_no_hope(self, monitor):
        result = assess(monitor, "I have no hope left for anything.")
        assert result["risk_level"] == RiskLevel.MEDIUM.value

    def test_intervention_type_is_direct_concern(self, monitor):
        result = assess(monitor, "I feel completely worthless.")
        assert result["intervention_type"] == InterventionType.DIRECT_CONCERN.value


# =============================================================================
# LOW RISK — must fire
# =============================================================================

class TestLowRisk:

    def test_want_to_disappear(self, monitor):
        result = assess(monitor, "Sometimes I just want to disappear.")
        assert result["risk_level"] in [RiskLevel.LOW.value, RiskLevel.MEDIUM.value]
        assert result["requires_followup"] is True

    def test_fade_away(self, monitor):
        result = assess(monitor, "I just want to fade away from everything.")
        assert result["risk_level"] in [RiskLevel.LOW.value, RiskLevel.MEDIUM.value]

    def test_intervention_type_is_check_in(self, monitor):
        result = assess(monitor, "Sometimes I just want to not be here anymore.")
        assert result["intervention_type"] in [
            InterventionType.GENTLE_CHECK_IN.value,
            InterventionType.DIRECT_CONCERN.value
        ]


# =============================================================================
# NEGATION HANDLING — should not trigger or should reduce risk
# =============================================================================

class TestNegation:

    def test_dont_want_to_kill_myself(self, monitor):
        result = assess(monitor, "I don't want to kill myself, I just feel lost.")
        # Should not be CRITICAL — negation should suppress
        assert result["risk_level"] != RiskLevel.CRITICAL.value

    def test_never_thought_about_suicide(self, monitor):
        result = assess(monitor, "I've never thought about suicide.")
        assert result["risk_level"] == RiskLevel.NONE.value

    def test_used_to_want_to_die(self, monitor):
        result = assess(monitor, "I used to want to die but I feel better now.")
        # Past tense negation — should not be CRITICAL
        assert result["risk_level"] != RiskLevel.CRITICAL.value

    def test_afraid_of_dying(self, monitor):
        result = assess(monitor, "I'm scared of dying, not wanting to die.")
        assert result["risk_level"] != RiskLevel.CRITICAL.value

    def test_joking_context(self, monitor):
        result = assess(monitor, "Only joking about the end it all bit, I'm fine.")
        assert result["risk_level"] != RiskLevel.CRITICAL.value


# =============================================================================
# CONTEXT MULTIPLIERS — should escalate risk
# =============================================================================

class TestMultipliers:

    def test_substances_escalate_medium_to_high(self, monitor):
        result = assess(
            monitor,
            "I've been drinking heavily and I just feel worthless."
        )
        # worthless = MEDIUM, drinking heavily = multiplier → HIGH
        assert result["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
        assert result["context_multipliers_present"] is True

    def test_isolation_escalates(self, monitor):
        result = assess(
            monitor,
            "I'm completely alone and I just can't see a way out."
        )
        assert result["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]

    def test_means_mentioned_escalates(self, monitor):
        result = assess(
            monitor,
            "I feel worthless and there's a gun in the house."
        )
        assert result["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]

    def test_finality_escalates(self, monitor):
        result = assess(
            monitor,
            "This is the last time I'll feel this way, goodbye."
        )
        assert result["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]

    def test_multiplier_flag_set(self, monitor):
        result = assess(
            monitor,
            "I've been drinking and I hate myself."
        )
        assert result["context_multipliers_present"] is True


# =============================================================================
# EMOTIONAL INTENSITY ESCALATION
# =============================================================================

class TestEmotionalIntensity:

    def test_high_intensity_escalates_medium_to_high(self, monitor):
        result = assess(
            monitor,
            "I feel completely worthless.",
            intensity=0.85,
            state="depressed"
        )
        assert result["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]

    def test_extreme_intensity_escalates_high_to_critical(self, monitor):
        result = assess(
            monitor,
            "There's no reason to live anymore.",
            intensity=0.95,
            state="depressed"
        )
        assert result["risk_level"] == RiskLevel.CRITICAL.value

    def test_low_intensity_does_not_escalate(self, monitor):
        result = assess(
            monitor,
            "I feel a bit worthless today.",
            intensity=0.2,
            state="neutral"
        )
        assert result["risk_level"] == RiskLevel.MEDIUM.value


# =============================================================================
# HISTORICAL PATTERN DETECTION
# =============================================================================

class TestHistoricalPatterns:

    def test_persistent_depression_escalates(self, monitor):
        history = [
            {"state": "depressed", "intensity": 0.7, "primary_emotion": "depressed"},
            {"state": "depressed", "intensity": 0.7, "primary_emotion": "depressed"},
            {"state": "depressed", "intensity": 0.7, "primary_emotion": "depressed"},
        ]
        result = monitor.assess_safety(
            message="I feel worthless.",
            emotional_context=make_emotional_context(0.5, "depressed"),
            emotional_history=history
        )
        assert result["risk_level"] in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
        assert "persistent_depression_pattern" in result["safety_concerns"]

    def test_anxiety_to_depression_shift_flagged(self, monitor):
        history = [
            {"state": "anxious", "intensity": 0.6, "primary_emotion": "anxious"},
            {"state": "anxious", "intensity": 0.6, "primary_emotion": "anxious"},
            {"state": "depressed", "intensity": 0.7, "primary_emotion": "depressed"},
        ]
        result = monitor.assess_safety(
            message="I don't know how to keep going.",
            emotional_context=make_emotional_context(0.6, "depressed"),
            emotional_history=history
        )
        triggers = result["specific_triggers"]
        assert any("anxiety to depression" in t for t in triggers)


# =============================================================================
# FAIL SAFE
# =============================================================================

class TestFailSafe:

    def test_none_message_returns_high_risk(self, monitor):
        """If message is None, assessment must fail safe."""
        result = monitor.assess_safety(
            message=None,
            emotional_context={},
            emotional_history=[]
        )
        assert result["risk_level"] == RiskLevel.HIGH.value
        assert result["requires_intervention"] is True

    def test_corrupt_emotional_context_fails_safe(self, monitor):
        """If emotional context is malformed, must fail safe."""
        result = monitor.assess_safety(
            message="I feel okay today.",
            emotional_context="this is not a dict",
            emotional_history=[]
        )
        assert result["risk_level"] == RiskLevel.HIGH.value

    def test_error_flag_present_on_fail_safe(self, monitor):
        result = monitor.assess_safety(
            message=None,
            emotional_context={},
            emotional_history=[]
        )
        assert "error" in result


# =============================================================================
# ASSESSMENT STRUCTURE — verify output shape is always consistent
# =============================================================================

class TestAssessmentStructure:

    def test_required_keys_present_clean_message(self, monitor):
        result = assess(monitor, "I'm doing okay today.")
        required_keys = [
            "risk_level",
            "risk_score",
            "safety_concerns",
            "specific_triggers",
            "intervention_type",
            "requires_intervention",
            "requires_followup",
            "emergency_contact_suggested",
            "emotional_intensity",
            "context_multipliers_present",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_required_keys_present_high_risk(self, monitor):
        result = assess(monitor, "I want to end my life.")
        required_keys = [
            "risk_level",
            "risk_score",
            "safety_concerns",
            "specific_triggers",
            "intervention_type",
            "requires_intervention",
            "requires_followup",
            "emergency_contact_suggested",
            "emotional_intensity",
            "context_multipliers_present",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_risk_score_is_positive_on_detection(self, monitor):
        result = assess(monitor, "I want to end my life.")
        assert result["risk_score"] > 0

    def test_risk_score_is_zero_on_clean(self, monitor):
        result = assess(monitor, "Had a great day today.")
        assert result["risk_score"] == 0.0
