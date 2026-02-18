"""
Enhanced Safety Monitor - Multi-level crisis detection
Part of the Veteran AI Safety Layer
https://github.com/TheAIOldtimer/veteran-ai-safety-layer

⚠️  CRITICAL: This is the most important safety feature in the stack.
    Any changes to this file should be reviewed carefully.
    When in doubt, this system FAILS SAFE — it assumes risk rather than dismisses it.

CALL ORDER:
    User message
        → emotion_tracker.py   (detect emotional state first)
        → safety_monitor.py    (assess risk using emotional context)
        → persona response     (shaped by both outputs)
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS — self-contained, no external dependencies
# =============================================================================

class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InterventionType(Enum):
    NONE = "none"
    GENTLE_CHECK_IN = "gentle_check_in"
    DIRECT_CONCERN = "direct_concern"
    CRISIS_RESPONSE = "crisis_response"
    EMERGENCY_RESOURCES = "emergency_resources"


# =============================================================================
# SAFETY MONITOR
# =============================================================================

class EnhancedSafetyMonitor:
    """
    Multi-level safety monitoring with comprehensive crisis detection.

    Risk levels:
        CRITICAL  — immediate danger, emergency resources required
        HIGH      — serious ideation, crisis response required
        MEDIUM    — self-harm or severe distress signals
        LOW       — passive ideation, gentle check-in warranted
        NONE      — no safety flags detected

    Fail-safe behaviour:
        If the assessment itself throws an error, the system returns HIGH risk
        and flags for intervention. Never silently fails.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.safety_history: deque = deque(maxlen=20)

        # =====================================================================
        # CRITICAL KEYWORDS — immediate danger
        # =====================================================================
        self.critical_keywords = [
            # Direct statements
            "kill myself", "end my life", "suicide", "want to die",
            "going to kill myself", "plan to die", "planning to die",
            "going to end it", "end it all tonight", "end it all today",

            # Informal / regional expressions
            "snuff myself", "do myself in", "top myself", "off myself",
            "end it", "finish it", "done with life",

            # Method mentions
            "jump off", "overdose", "pills and", "cut my wrists",
            "hang myself", "hanging myself",

            # Finality statements
            "goodbye forever", "last time", "won't be here tomorrow",
            "this is it", "final message", "saying goodbye",
        ]

        # =====================================================================
        # HIGH RISK KEYWORDS — serious ideation
        # =====================================================================
        self.high_risk_keywords = [
            "don't want to live", "can't go on", "no reason to live",
            "better off dead", "world better without me",
            "shouldn't be here", "wish I was dead", "wish I wasn't here",
            "don't want to be here anymore", "can't do this anymore",
            "too much to bear", "can't take it anymore",

            # Informal / regional expressions
            "rather be dead", "had enough of life", "done with it all",
            "can't cope", "end of my tether", "at the end",

            # Burden statements
            "burden on everyone", "burden to", "everyone better off",
            "tired of being a burden", "they'd be better without me",
        ]

        # =====================================================================
        # MEDIUM RISK KEYWORDS — self-harm or severe distress
        # =====================================================================
        self.medium_risk_keywords = [
            "hurt myself", "harm myself", "cut myself", "cutting myself",
            "burn myself", "punish myself", "self harm", "self-harm",
            "hate myself", "worthless", "piece of shit", "waste of space",
            "hopeless", "no hope", "give up", "giving up",
            "pointless", "no point", "what's the point",
            "can't see a way out", "trapped", "no escape", "no future",
            "nothing left", "empty inside", "numb", "dead inside",
        ]

        # =====================================================================
        # LOW RISK KEYWORDS — passive ideation, no stated plan
        # =====================================================================
        self.ideation_keywords = [
            "wish i was dead", "wish i wasn't here", "shouldn't exist",
            "world better without me", "disappear", "fade away",
            "stop existing", "not be here", "be gone",
        ]

        # =====================================================================
        # CONTEXT MULTIPLIERS — escalate risk when present alongside keywords
        # =====================================================================
        self.risk_multipliers = {
            "substances": ["drunk", "drinking", "high", "pills", "alcohol", "drugs"],
            "isolation":  ["alone", "no one", "nobody", "by myself", "isolated"],
            "finality":   ["goodbye", "last", "final", "forever", "never again"],
            "means":      ["gun", "pills", "bridge", "rope", "blade", "knife"],
        }

    # =========================================================================
    # MAIN ASSESSMENT METHOD
    # =========================================================================

    def assess_safety(
        self,
        message: str,
        emotional_context: Dict[str, Any],
        emotional_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Comprehensive safety assessment with context-aware detection.

        Args:
            message:            Raw user message text
            emotional_context:  Output from emotion_tracker.record_emotion()
            emotional_history:  Output from emotion_tracker.get_emotional_history()

        Returns:
            Assessment dict — always returned, never raises.
            On error, returns HIGH risk as a fail-safe.
        """
        try:
            text = message.lower()
            intensity = emotional_context.get("emotional_intensity", 0)

            risk_level = RiskLevel.NONE
            safety_concerns = []
            specific_triggers = []
            risk_score = 0.0

            # =================================================================
            # PHASE 1: Direct keyword matching
            # =================================================================

            for keyword in self.critical_keywords:
                if keyword in text:
                    risk_level = RiskLevel.CRITICAL
                    safety_concerns.append("immediate_suicide_risk")
                    specific_triggers.append(f"critical: '{keyword}'")
                    risk_score += 10.0
                    logger.critical(
                        f"CRITICAL SAFETY ALERT: user={self.user_id} "
                        f"phrase='{keyword}'"
                    )
                    break

            if risk_level != RiskLevel.CRITICAL:
                for keyword in self.high_risk_keywords:
                    if keyword in text:
                        risk_level = RiskLevel.HIGH
                        safety_concerns.append("high_suicide_risk")
                        specific_triggers.append(f"high: '{keyword}'")
                        risk_score += 7.0
                        logger.error(
                            f"HIGH RISK ALERT: user={self.user_id} "
                            f"phrase='{keyword}'"
                        )
                        break

            if risk_level not in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                for keyword in self.medium_risk_keywords:
                    if keyword in text:
                        risk_level = RiskLevel.MEDIUM
                        safety_concerns.append("self_harm_risk")
                        specific_triggers.append(f"medium: '{keyword}'")
                        risk_score += 5.0
                        logger.warning(
                            f"MEDIUM RISK: user={self.user_id} "
                            f"phrase='{keyword}'"
                        )
                        break

            if risk_level == RiskLevel.NONE:
                for keyword in self.ideation_keywords:
                    if keyword in text:
                        risk_level = RiskLevel.LOW
                        safety_concerns.append("suicidal_ideation")
                        specific_triggers.append(f"ideation: '{keyword}'")
                        risk_score += 3.0
                        logger.info(
                            f"LOW RISK: user={self.user_id} ideation detected"
                        )
                        break

            # =================================================================
            # PHASE 2: Context multipliers — escalate if present
            # =================================================================

            multiplier_found = False
            for category, keywords in self.risk_multipliers.items():
                if any(kw in text for kw in keywords):
                    multiplier_found = True
                    specific_triggers.append(f"multiplier: {category}")
                    risk_score += 2.0

                    if risk_level == RiskLevel.MEDIUM:
                        risk_level = RiskLevel.HIGH
                        logger.warning(
                            f"Risk escalated to HIGH — multiplier: {category} "
                            f"user={self.user_id}"
                        )
                    elif risk_level == RiskLevel.HIGH:
                        risk_level = RiskLevel.CRITICAL
                        logger.critical(
                            f"Risk escalated to CRITICAL — multiplier: {category} "
                            f"user={self.user_id}"
                        )

            # =================================================================
            # PHASE 3: Emotional intensity amplification
            # =================================================================

            if intensity > 0.8:
                risk_score += 2.0
                specific_triggers.append(f"high_emotional_intensity: {intensity:.2f}")

                if risk_level == RiskLevel.MEDIUM and intensity > 0.8:
                    risk_level = RiskLevel.HIGH
                    logger.warning(
                        f"Risk escalated to HIGH — emotional intensity "
                        f"user={self.user_id}"
                    )
                elif risk_level == RiskLevel.HIGH and intensity > 0.9:
                    risk_level = RiskLevel.CRITICAL
                    logger.critical(
                        f"Risk escalated to CRITICAL — extreme intensity "
                        f"user={self.user_id}"
                    )

            # =================================================================
            # PHASE 4: Historical pattern detection
            # =================================================================

            if emotional_history and len(emotional_history) >= 3:
                recent_states = [e.get("state") for e in emotional_history[-3:]]

                if recent_states.count("depressed") >= 2:
                    safety_concerns.append("persistent_depression_pattern")
                    specific_triggers.append("pattern: persistent depression")

                    if risk_level == RiskLevel.MEDIUM:
                        risk_level = RiskLevel.HIGH
                        logger.warning(
                            f"Risk escalated to HIGH — depression pattern "
                            f"user={self.user_id}"
                        )

                if "anxious" in recent_states[:2] and recent_states[-1] == "depressed":
                    specific_triggers.append("pattern: anxiety to depression shift")
                    risk_score += 1.0

            # =================================================================
            # PHASE 5: Select intervention type
            # =================================================================

            intervention_type = self._select_intervention_type(
                risk_level,
                safety_concerns,
                multiplier_found
            )

            # =================================================================
            # PHASE 6: Build and return assessment
            # =================================================================

            assessment = {
                "risk_level": risk_level.value,
                "risk_score": risk_score,
                "safety_concerns": safety_concerns,
                "specific_triggers": specific_triggers,
                "intervention_type": intervention_type.value,
                "requires_intervention": risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH],
                "requires_followup": risk_level in [RiskLevel.MEDIUM, RiskLevel.LOW],
                "emergency_contact_suggested": risk_level == RiskLevel.CRITICAL,
                "emotional_intensity": intensity,
                "context_multipliers_present": multiplier_found,
            }

            self.safety_history.append({
                "timestamp": datetime.utcnow(),
                "risk_level": risk_level.value,
                "concerns": safety_concerns,
                "triggers": specific_triggers
            })

            if risk_level != RiskLevel.NONE:
                logger.warning(
                    f"Safety assessment — user={self.user_id} "
                    f"risk={risk_level.value} "
                    f"score={risk_score:.1f} "
                    f"triggers={len(specific_triggers)}"
                )

            return assessment

        except Exception as e:
            # FAIL SAFE — if assessment errors, always assume risk
            logger.error(f"Safety assessment failed for {self.user_id}: {e}")
            return {
                "risk_level": RiskLevel.HIGH.value,
                "safety_concerns": ["assessment_error"],
                "intervention_type": InterventionType.CRISIS_RESPONSE.value,
                "requires_intervention": True,
                "requires_followup": True,
                "emergency_contact_suggested": True,
                "error": str(e)
            }

    # =========================================================================
    # INTERVENTION SELECTION
    # =========================================================================

    def _select_intervention_type(
        self,
        risk_level: RiskLevel,
        concerns: List[str],
        has_multipliers: bool
    ) -> InterventionType:
        """Select appropriate intervention based on risk assessment"""

        if risk_level == RiskLevel.CRITICAL:
            return InterventionType.EMERGENCY_RESOURCES
        elif risk_level == RiskLevel.HIGH:
            if has_multipliers:
                return InterventionType.EMERGENCY_RESOURCES
            return InterventionType.CRISIS_RESPONSE
        elif risk_level == RiskLevel.MEDIUM:
            return InterventionType.DIRECT_CONCERN
        elif risk_level == RiskLevel.LOW:
            return InterventionType.GENTLE_CHECK_IN
        else:
            return InterventionType.NONE
