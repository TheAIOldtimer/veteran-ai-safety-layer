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

KNOWN LIMITATIONS:
    - Keyword matching is rule-based, not semantic. It will miss novel phrasing.
    - Negation handling covers common patterns but is not exhaustive.
    - Slang, code-switching, and non-English input are not fully covered.
    - This is a safety scaffold, not a clinical instrument.
    - Always pair with human safeguarding oversight in production.
    - See SAFEGUARDING_DISCLAIMER.md before deploying.
"""

import re
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
# TEXT NORMALISATION HELPERS
# =============================================================================

def normalise_text(text: str) -> str:
    """
    Normalise input text before matching.

    - Lowercase
    - Collapse whitespace (catches 'kill  myself', 'k i l l myself')
    - Remove repeated punctuation
    - Preserve word boundaries
    """
    text = text.lower()
    # Collapse multiple spaces, tabs, newlines
    text = re.sub(r'\s+', ' ', text)
    # Remove repeated punctuation (e.g. '...' → '.', '!!!' → '!')
    text = re.sub(r'([^\w\s])\1+', r'\1', text)
    return text.strip()


def build_pattern(phrase: str) -> re.Pattern:
    """
    Build a word-boundary-aware regex pattern for a phrase.

    Handles:
    - Word boundaries on first and last token
    - Optional punctuation between words
    - Common spelling variants with optional characters

    Args:
        phrase: The keyword phrase to compile

    Returns:
        Compiled regex pattern
    """
    # Escape the phrase, then replace spaces with flexible whitespace
    escaped = re.escape(phrase)
    # Allow one or more whitespace characters between words
    flexible = escaped.replace(r'\ ', r'\s+')
    # Wrap in word boundaries
    pattern = r'\b' + flexible + r'\b'
    return re.compile(pattern, re.IGNORECASE)


# Negation words that typically precede a concerning phrase
NEGATION_PREFIXES = [
    "don't want to", "do not want to",
    "never", "not going to", "won't",
    "wouldn't", "didn't", "doesn't",
    "used to", "used to want to",
    "thought about", "used to think about",
    "afraid of", "scared of", "fear",
    "wouldn't want to", "would never",
    "joking", "just joking", "only joking",
    "not", "no longer", "not anymore",
]

NEGATION_WINDOW = 8  # Words to look back for negation context


def is_negated(text: str, match_start: int) -> bool:
    """
    Check if a match is preceded by a negation phrase within a word window.

    Args:
        text:        Full normalised message text
        match_start: Character position of the match start

    Returns:
        True if the phrase appears to be negated
    """
    # Get the text before the match, up to NEGATION_WINDOW words back
    preceding = text[:match_start]
    preceding_words = preceding.split()
    window = " ".join(preceding_words[-NEGATION_WINDOW:])

    for negation in NEGATION_PREFIXES:
        if negation in window:
            return True
    return False


# =============================================================================
# SAFETY MONITOR
# =============================================================================

class EnhancedSafetyMonitor:
    """
    Multi-level safety monitoring with crisis detection.

    Risk levels:
        CRITICAL  — immediate danger, emergency resources required
        HIGH      — serious ideation, crisis response required
        MEDIUM    — self-harm or severe distress signals
        LOW       — passive ideation, gentle check-in warranted
        NONE      — no safety flags detected

    Matching approach:
        - Text is normalised before matching (whitespace, case, punctuation)
        - Word-boundary regex prevents substring false positives
        - Negation window check reduces false positives from context
        - Context multipliers escalate risk when co-occurring signals present

    Fail-safe behaviour:
        If the assessment itself throws an error, the system returns HIGH risk
        and flags for intervention. Never silently fails.

    Known limitations:
        See module docstring above.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.safety_history: deque = deque(maxlen=20)

        # =====================================================================
        # CRITICAL KEYWORDS — immediate danger
        # Compiled to regex patterns at init for performance
        # =====================================================================
        self.critical_keywords = [
            "kill myself", "end my life", "suicide", "want to die",
            "going to kill myself", "plan to die", "planning to die",
            "going to end it all", "end it all tonight", "end it all today",
            "snuff myself", "do myself in", "top myself", "off myself",
            "done with life",
            "jump off a bridge", "overdose on", "cut my wrists",
            "hang myself", "hanging myself",
            "goodbye forever", "won't be here tomorrow",
            "final message", "saying goodbye forever",
        ]

        # =====================================================================
        # HIGH RISK KEYWORDS — serious ideation
        # =====================================================================
        self.high_risk_keywords = [
            "don't want to live", "cant go on", "no reason to live",
            "better off dead", "world better without me",
            "shouldn't be here", "wish i was dead", "wish i wasn't here",
            "don't want to be here anymore", "can't do this anymore",
            "too much to bear", "can't take it anymore",
            "rather be dead", "had enough of life", "done with it all",
            "end of my tether",
            "burden on everyone", "everyone better off without me",
            "tired of being a burden", "they'd be better without me",
        ]

        # =====================================================================
        # MEDIUM RISK KEYWORDS — self-harm or severe distress
        # =====================================================================
        self.medium_risk_keywords = [
            "hurt myself", "harm myself", "cut myself", "cutting myself",
            "burn myself", "punish myself", "self harm", "self-harm",
            "hate myself", "worthless", "waste of space",
            "no hope", "giving up on life",
            "can't see a way out", "no escape", "no future",
            "nothing left", "dead inside",
        ]

        # =====================================================================
        # LOW RISK KEYWORDS — passive ideation, no stated plan
        # =====================================================================
        self.ideation_keywords = [
            "wish i was dead", "wish i wasn't here", "shouldn't exist",
            "want to disappear", "want to fade away",
            "stop existing", "not be here anymore",
        ]

        # =====================================================================
        # INFORMAL / ABBREVIATION PATTERNS
        # These are matched separately without word boundaries
        # as they are already atomic tokens
        # =====================================================================
        self.informal_critical = [
            r'\bkms\b',    # kill myself
            r'\bkys\b',    # kill yourself (directed or self-directed)
            r'\bnhs\b',    # no hope syndrome (context-dependent, low signal)
        ]

        # =====================================================================
        # CONTEXT MULTIPLIERS — escalate risk when present alongside keywords
        # =====================================================================
        self.risk_multipliers = {
            "substances": [
                "drunk", "drinking heavily", "high on", "took pills",
                "alcohol", "on drugs", "been drinking"
            ],
            "isolation": [
                "all alone", "no one cares", "nobody cares",
                "completely alone", "isolated", "no one to talk to"
            ],
            "finality": [
                "goodbye", "last time", "final", "forever",
                "never again", "one last"
            ],
            "means": [
                "gun", "firearm", "pills", "bridge",
                "rope", "blade", "knife", "medication"
            ],
        }

        # Pre-compile all patterns at init for performance
        self._compiled_critical = [build_pattern(k) for k in self.critical_keywords]
        self._compiled_high = [build_pattern(k) for k in self.high_risk_keywords]
        self._compiled_medium = [build_pattern(k) for k in self.medium_risk_keywords]
        self._compiled_ideation = [build_pattern(k) for k in self.ideation_keywords]
        self._compiled_informal = [re.compile(p, re.IGNORECASE) for p in self.informal_critical]
        self._compiled_multipliers = {
            cat: [build_pattern(k) for k in keywords]
            for cat, keywords in self.risk_multipliers.items()
        }

    # =========================================================================
    # CORE MATCHING
    # =========================================================================

    def _match(
        self,
        text: str,
        patterns: List[re.Pattern],
        check_negation: bool = True
    ):
        """
        Attempt to match any pattern against normalised text.

        Args:
            text:             Normalised message text
            patterns:         List of compiled regex patterns
            check_negation:   Whether to check for negation context

        Returns:
            Matched keyword string or None
        """
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                if check_negation and is_negated(text, match.start()):
                    logger.info(
                        f"Negated match skipped: '{match.group()}' "
                        f"user={self.user_id}"
                    )
                    continue
                return match.group()
        return None

    # =========================================================================
    # MAIN ASSESSMENT
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
            # Normalise text once, reuse throughout
            text = normalise_text(message)
            intensity = emotional_context.get("emotional_intensity", 0)

            risk_level = RiskLevel.NONE
            safety_concerns = []
            specific_triggers = []
            risk_score = 0.0

            # =================================================================
            # PHASE 1: Direct keyword matching
            # =================================================================

            # CRITICAL
            matched = self._match(text, self._compiled_critical)
            if not matched:
                # Also check informal patterns (no negation check — these are
                # typically unambiguous)
                matched = self._match(
                    text, self._compiled_informal, check_negation=False
                )
            if matched:
                risk_level = RiskLevel.CRITICAL
                safety_concerns.append("immediate_suicide_risk")
                specific_triggers.append(f"critical: '{matched}'")
                risk_score += 10.0
                logger.critical(
                    f"CRITICAL SAFETY ALERT: user={self.user_id} "
                    f"phrase='{matched}'"
                )

            # HIGH
            if risk_level != RiskLevel.CRITICAL:
                matched = self._match(text, self._compiled_high)
                if matched:
                    risk_level = RiskLevel.HIGH
                    safety_concerns.append("high_suicide_risk")
                    specific_triggers.append(f"high: '{matched}'")
                    risk_score += 7.0
                    logger.error(
                        f"HIGH RISK ALERT: user={self.user_id} "
                        f"phrase='{matched}'"
                    )

            # MEDIUM
            if risk_level not in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                matched = self._match(text, self._compiled_medium)
                if matched:
                    risk_level = RiskLevel.MEDIUM
                    safety_concerns.append("self_harm_risk")
                    specific_triggers.append(f"medium: '{matched}'")
                    risk_score += 5.0
                    logger.warning(
                        f"MEDIUM RISK: user={self.user_id} "
                        f"phrase='{matched}'"
                    )

            # LOW
            if risk_level == RiskLevel.NONE:
                matched = self._match(text, self._compiled_ideation)
                if matched:
                    risk_level = RiskLevel.LOW
                    safety_concerns.append("suicidal_ideation")
                    specific_triggers.append(f"ideation: '{matched}'")
                    risk_score += 3.0
                    logger.info(
                        f"LOW RISK: user={self.user_id} ideation detected"
                    )

            # =================================================================
            # PHASE 2: Context multipliers
            # =================================================================

            multiplier_found = False
            for category, patterns in self._compiled_multipliers.items():
                matched_multiplier = self._match(
                    text, patterns, check_negation=False
                )
                if matched_multiplier:
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
                specific_triggers.append(
                    f"high_emotional_intensity: {intensity:.2f}"
                )

                if risk_level == RiskLevel.MEDIUM:
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
                recent_states = [
                    e.get("state") for e in emotional_history[-3:]
                ]

                if recent_states.count("depressed") >= 2:
                    safety_concerns.append("persistent_depression_pattern")
                    specific_triggers.append("pattern: persistent depression")

                    if risk_level == RiskLevel.MEDIUM:
                        risk_level = RiskLevel.HIGH
                        logger.warning(
                            f"Risk escalated to HIGH — depression pattern "
                            f"user={self.user_id}"
                        )

                if (
                    "anxious" in recent_states[:2]
                    and recent_states[-1] == "depressed"
                ):
                    specific_triggers.append(
                        "pattern: anxiety to depression shift"
                    )
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
                "risk_level":                 risk_level.value,
                "risk_score":                 risk_score,
                "safety_concerns":            safety_concerns,
                "specific_triggers":          specific_triggers,
                "intervention_type":          intervention_type.value,
                "requires_intervention":      risk_level in [
                    RiskLevel.CRITICAL, RiskLevel.HIGH
                ],
                "requires_followup":          risk_level in [
                    RiskLevel.MEDIUM, RiskLevel.LOW
                ],
                "emergency_contact_suggested": risk_level == RiskLevel.CRITICAL,
                "emotional_intensity":        intensity,
                "context_multipliers_present": multiplier_found,
            }

            self.safety_history.append({
                "timestamp":  datetime.utcnow(),
                "risk_level": risk_level.value,
                "concerns":   safety_concerns,
                "triggers":   specific_triggers
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
            logger.error(
                f"Safety assessment failed for {self.user_id}: {e}"
            )
            return {
                "risk_level":                 RiskLevel.HIGH.value,
                "safety_concerns":            ["assessment_error"],
                "intervention_type":          InterventionType.CRISIS_RESPONSE.value,
                "requires_intervention":      True,
                "requires_followup":          True,
                "emergency_contact_suggested": True,
                "error":                      str(e)
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
        """Select appropriate intervention based on risk assessment."""

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
