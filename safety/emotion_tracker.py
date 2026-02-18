"""
Emotion Tracker - Track emotional patterns over time
Part of the Veteran AI Safety Layer
https://github.com/TheAIOldtimer/veteran-ai-safety-layer
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import deque

logger = logging.getLogger(__name__)


class EmotionTracker:
    """
    Tracks emotional patterns across a session.
    Run this BEFORE safety_monitor.py on every message.
    The safety monitor depends on the output from this class.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.emotion_history: deque = deque(maxlen=50)
        self.session_emotions: List[Dict[str, Any]] = []

    def record_emotion(self, emotional_analysis: Dict[str, Any]):
        """Record emotional snapshot from the parsed analysis"""
        snapshot = {
            "timestamp": datetime.utcnow(),
            "primary_emotion": emotional_analysis.get("primary_emotion"),
            "intensity": emotional_analysis.get("emotional_intensity", 0),
            "state": emotional_analysis.get("emotional_state"),
            "detected_emotions": emotional_analysis.get("detected_emotions", [])
        }
        self.emotion_history.append(snapshot)
        self.session_emotions.append(snapshot)

    def get_emotional_history(self) -> List[Dict[str, Any]]:
        """Get recent emotional history for use by safety monitor"""
        return list(self.emotion_history)

    def get_emotional_summary(self) -> str:
        """
        Get natural language summary of emotional patterns.
        Use this to inform persona response tone.
        """
        if len(self.emotion_history) < 3:
            return ""

        recent = list(self.emotion_history)[-10:]
        emotions = [e["primary_emotion"] for e in recent]
        intensities = [e["intensity"] for e in recent]

        avg_intensity = sum(intensities) / len(intensities)
        dominant_emotion = max(set(emotions), key=emotions.count)

        if len(intensities) >= 5:
            recent_avg = sum(intensities[-3:]) / 3
            earlier_avg = sum(intensities[-6:-3]) / 3

            if recent_avg > earlier_avg + 0.2:
                trend = "intensifying"
            elif recent_avg < earlier_avg - 0.2:
                trend = "calming"
            else:
                trend = "stable"
        else:
            trend = "emerging"

        return (
            f"Recent emotional pattern: {dominant_emotion} "
            f"(intensity: {avg_intensity:.1f}/1.0, trend: {trend}). "
            f"Use this to inform response tone, not to label the user."
        )

    def get_recent_pattern_summary(self) -> str:
        """Get brief recent pattern — useful for session continuity"""
        if len(self.emotion_history) < 2:
            return ""
        last = self.emotion_history[-1]
        return f"Last interaction: {last['primary_emotion']} (intensity: {last['intensity']:.1f})"

    def has_significant_emotional_event(self) -> bool:
        """Returns True if the last message was emotionally intense (>0.7)"""
        if not self.emotion_history:
            return False
        return self.emotion_history[-1]["intensity"] > 0.7

    def get_current_state(self) -> str:
        """Get current emotional state label"""
        if not self.emotion_history:
            return "unknown"
        return self.emotion_history[-1].get("state", "unknown")

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Summary of the emotional journey this session.
        Use at end-of-session for memory consolidation decisions.
        """
        if not self.session_emotions:
            return {}

        emotions = [e["primary_emotion"] for e in self.session_emotions]
        intensities = [e["intensity"] for e in self.session_emotions]

        return {
            "emotion_range": list(set(emotions)),
            "avg_intensity": sum(intensities) / len(intensities),
            "max_intensity": max(intensities),
            "dominant_emotion": max(set(emotions), key=emotions.count),
            "interaction_count": len(self.session_emotions)
        }

    def has_data(self) -> bool:
        """Check if tracker has any data this session"""
        return len(self.session_emotions) > 0
