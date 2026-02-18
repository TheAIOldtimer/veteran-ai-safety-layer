"""
Memory Manager - Central orchestrator for the multi-tier memory system
Part of the Veteran AI Safety Layer
https://github.com/TheAIOldtimer/veteran-ai-safety-layer

Orchestrates:
    - Micro memories (session summaries with decay)
    - Memory consolidation (long-term patterns)
    - Values context (core beliefs for persona grounding)
    - Smart retrieval with relevance scoring

STACK:
    Firebase Admin 6.2.0
    OpenAI SDK 1.3.0  (from openai import OpenAI)
    Firestore via firebase_admin.firestore

ENCRYPTION NOTE:
    Encryption stubs are in micro_memory.py.
    Replace encrypt_text() / decrypt_text() with your own implementation
    before going to production.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from firebase_admin import firestore
from openai import OpenAI

from .micro_memory import MicroMemory
from .memory_consolidator import MemoryConsolidator

logger = logging.getLogger(__name__)


# =============================================================================
# VALUE DEFINITIONS
# Used by the persona to ground responses in what matters to the user.
# Override with user-specific definitions from onboarding if available.
# =============================================================================

VALUE_DEFINITIONS = {
    "Honesty":      "Being truthful and transparent in all interactions",
    "Integrity":    "Doing the right thing even when no one is watching",
    "Loyalty":      "Standing by those who matter, through thick and thin",
    "Respect":      "Treating others with dignity and consideration",
    "Courage":      "Facing fear and adversity with strength",
    "Compassion":   "Showing kindness and understanding to others",
    "Family":       "Prioritising the bonds that anchor you",
    "Freedom":      "Valuing independence and self-determination",
    "Justice":      "Standing up for what's fair and right",
    "Faith":        "Holding onto beliefs that give life meaning",
    "Service":      "Giving back and helping others",
    "Honour":       "Living with dignity and keeping your word",
    "Duty":         "Fulfilling responsibilities without complaint",
    "Resilience":   "Bouncing back from setbacks and staying strong",
    "Growth":       "Continuously learning and improving yourself",
    "Independence": "Being self-reliant and capable",
    "Community":    "Contributing to something bigger than yourself",
    "Creativity":   "Expressing yourself and thinking differently",
    "Adventure":    "Embracing new experiences and challenges",
    "Peace":        "Seeking calm and harmony in life",
}


# =============================================================================
# SIMPLE PERSISTENT FACTS STORE
# Lightweight replacement for the full PersistentFacts subsystem.
# Stores key facts in Firestore under users/{user_id}/facts.
# Adapt or replace with your own implementation.
# =============================================================================

class SimpleFacts:
    """
    Minimal persistent facts store.
    Stores and retrieves categorised facts for a user.

    Adapt this to your own database or expand as needed.
    In production, encrypt sensitive fact values at rest.
    """

    def __init__(self, db: firestore.Client, user_id: str):
        self.db = db
        self.user_id = user_id
        self.ref = (
            self.db.collection("users")
            .document(user_id)
            .collection("facts")
        )

    def set_fact(self, category: str, key: str, value: Any, source: str = "user") -> bool:
        try:
            self.ref.document(f"{category}__{key}").set({
                "category": category,
                "key": key,
                "value": value,
                "source": source,
                "updated_at": datetime.utcnow().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Failed to set fact {category}/{key}: {e}")
            return False

    def get_fact(self, category: str, key: str) -> Optional[Any]:
        try:
            doc = self.ref.document(f"{category}__{key}").get()
            if doc.exists:
                return doc.to_dict().get("value")
            return None
        except Exception as e:
            logger.error(f"Failed to get fact {category}/{key}: {e}")
            return None

    def get_all_facts(self) -> Dict[str, Any]:
        try:
            facts = {}
            for doc in self.ref.stream():
                data = doc.to_dict()
                cat = data.get("category", "general")
                key = data.get("key", doc.id)
                facts.setdefault(cat, {})[key] = data.get("value")
            return facts
        except Exception as e:
            logger.error(f"Failed to get all facts: {e}")
            return {}

    def get_facts_for_prompt(self) -> str:
        """Format facts as a string for injection into the AI prompt."""
        try:
            all_facts = self.get_all_facts()
            if not all_facts:
                return ""

            lines = ["=== KNOWN ABOUT THIS USER ==="]
            for category, items in all_facts.items():
                if category == "values":
                    continue  # Handled separately by get_values_context()
                for key, value in items.items():
                    lines.append(f"  {key}: {value}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Failed to format facts for prompt: {e}")
            return ""

    def get_stats(self) -> Dict[str, Any]:
        try:
            docs = list(self.ref.stream())
            return {"total_facts": len(docs)}
        except Exception:
            return {"total_facts": 0}


# =============================================================================
# MEMORY MANAGER
# =============================================================================

class MemoryManager:
    """
    Central memory management system.

    Call order per session:
        1. add_message_to_session()  — after each message exchange
        2. end_session()             — when user disconnects or session times out

    Call order per prompt:
        1. get_context_for_prompt()  — inject memory context into system prompt
        2. get_values_context()      — inject values context if onboarding complete
    """

    def __init__(
        self,
        db: firestore.Client,
        user_id: str,
        openai_client: OpenAI
    ):
        self.db = db
        self.user_id = user_id
        self.openai_client = openai_client

        self.facts = SimpleFacts(db, user_id)
        self.micro = MicroMemory(db, user_id)
        self.consolidator = MemoryConsolidator(db, user_id, openai_client)

        self.current_session_messages: List[Dict[str, str]] = []
        self.session_start_time = datetime.utcnow()

        logger.info(f"Memory Manager initialised for user {user_id}")

    # =========================================================================
    # FACTS API
    # =========================================================================

    def set_fact(self, category: str, key: str, value: Any, source: str = "user") -> bool:
        return self.facts.set_fact(category, key, value, source)

    def get_fact(self, category: str, key: str) -> Optional[Any]:
        return self.facts.get_fact(category, key)

    def get_all_facts(self) -> Dict[str, Any]:
        return self.facts.get_all_facts()

    def import_onboarding(self, onboarding_data: Dict[str, Any]) -> int:
        """
        Import facts from onboarding data.

        Expects onboarding_data to be a flat or nested dict.
        Also handles core_values and value_definitions if present.
        """
        count = 0
        for key, value in onboarding_data.items():
            if key not in ("core_values", "value_definitions"):
                self.facts.set_fact("profile", key, value, "onboarding")
                count += 1

        if "core_values" in onboarding_data:
            values = onboarding_data["core_values"]
            if isinstance(values, list) and values:
                self.facts.set_fact("values", "core_values", values, "onboarding")
                count += 1

        if "value_definitions" in onboarding_data:
            definitions = onboarding_data["value_definitions"]
            if isinstance(definitions, dict):
                self.facts.set_fact("values", "value_definitions", definitions, "onboarding")
                count += 1

        logger.info(f"Imported {count} facts from onboarding for {self.user_id}")
        return count

    # =========================================================================
    # VALUES CONTEXT
    # =========================================================================

    def get_values_context(self) -> str:
        """
        Returns a natural language summary of the user's core values
        for injection into the AI system prompt.

        Returns empty string if no values have been set.
        """
        try:
            core_values = self.facts.get_fact("values", "core_values")

            if not core_values or not isinstance(core_values, list):
                return ""

            user_definitions = self.facts.get_fact("values", "value_definitions") or {}

            lines = [
                "USER'S CORE VALUES:",
                "These values are central to who this person is. "
                "Use them to ground your responses where relevant.",
                ""
            ]

            for value in core_values:
                definition = user_definitions.get(value) or VALUE_DEFINITIONS.get(value, "")
                if definition:
                    lines.append(f"  • {value}: {definition}")
                else:
                    lines.append(f"  • {value}")

            lines.append("")
            lines.append(
                "When relevant, connect what they're going through to what matters to them. "
                "These values can be a source of strength and grounding."
            )

            sources = self.facts.get_fact("values", "sources_of_meaning")
            if sources and isinstance(sources, list):
                lines.append(f"\nSources of meaning: {', '.join(sources)}")

            life_chapter = self.facts.get_fact("values", "life_chapter")
            if life_chapter:
                lines.append(f"Current life chapter: {life_chapter}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to get values context: {e}")
            return ""

    def user_has_value(self, value_name: str) -> bool:
        """Check if a specific value is in the user's core values."""
        core_values = self.facts.get_fact("values", "core_values")
        if not core_values or not isinstance(core_values, list):
            return False
        return value_name in core_values

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    def add_message_to_session(self, role: str, content: str):
        """
        Add a message to the current session buffer.
        Call this after every user message and every assistant reply.
        """
        self.current_session_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def end_session(self, reason: str = "logout") -> Optional[str]:
        """
        End the current session and write a micro memory to Firestore.

        Args:
            reason: Why the session ended (logout, timeout, etc.)

        Returns:
            micro_memory_id or None if session was too short to save
        """
        try:
            if len(self.current_session_messages) < 2:
                logger.info(f"Session too short to save (reason: {reason})")
                return None

            summary = await self._generate_session_summary()
            emotional_context = self._extract_session_emotions()
            topics = self._extract_session_topics()
            importance = self._calculate_session_importance(emotional_context, topics)

            micro_memory_id = self.micro.create_micro_memory(
                summary=summary,
                messages=self.current_session_messages,
                emotional_context=emotional_context,
                topics=topics,
                initial_importance=importance
            )

            if self.consolidator.check_consolidation_ready(self.micro):
                logger.info("Consolidation threshold reached, triggering...")
                await self.consolidator.consolidate_memories(self.micro)

            self.current_session_messages = []
            self.session_start_time = datetime.utcnow()

            return micro_memory_id

        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            return None

    # =========================================================================
    # PROMPT CONTEXT RETRIEVAL
    # =========================================================================

    def get_context_for_prompt(
        self,
        max_micro_memories: int = 5,
        relevance_threshold: float = 0.0
    ) -> str:
        """
        Get formatted memory context for injection into the AI system prompt.

        Args:
            max_micro_memories:  Max number of recent micro memories to include
            relevance_threshold: 0.0 = all, 0.6 = only high-relevance memories

        Returns:
            Formatted string, decrypted and ready for prompt injection
        """
        try:
            lines = []

            facts_text = self.facts.get_facts_for_prompt()
            if facts_text:
                lines.append(facts_text)
                lines.append("")

            recent_micros = self.micro.get_recent_micro_memories(
                limit=max_micro_memories,
                min_importance=max(2.0, relevance_threshold * 10),
                apply_decay=True
            )

            if recent_micros:
                lines.append("=== RECENT CONVERSATIONS ===")
                for memory in recent_micros:
                    lines.append(f"\nDate: {memory['created_at'][:10]}")
                    lines.append(f"Summary: {memory.get('summary', '')}")
                    lines.append(
                        f"Importance: {memory['current_importance']:.1f}/10"
                    )
                    emotional = memory.get("emotional_context", {})
                    if emotional.get("emotional_intensity", 0) > 0.5:
                        lines.append(
                            f"Emotion: {emotional.get('primary_emotion', 'unknown')} "
                            f"(intensity: {emotional.get('emotional_intensity', 0):.1f})"
                        )
                lines.append("")

            super_memories = self.consolidator.get_all_super_memories(limit=3)

            if super_memories:
                lines.append("=== LONG-TERM PATTERNS ===")
                for memory in super_memories:
                    lines.append(
                        f"\nPeriod: {memory['date_range']['start'][:10]} "
                        f"to {memory['date_range']['end'][:10]}"
                    )
                    lines.append(f"Summary: {memory.get('summary', '')}")
                    if memory.get("themes"):
                        lines.append(f"Themes: {', '.join(memory['themes'])}")
                lines.append("")

            return "\n".join(lines) if lines else ""

        except Exception as e:
            logger.error(f"Failed to get context for prompt: {e}")
            return ""

    def get_recent_open_thread(self) -> Optional[Dict[str, Any]]:
        """
        Find a recent high-importance or emotionally significant topic
        that may warrant a proactive follow-up.

        Returns:
            Dict with summary, topic, and date — or None
        """
        try:
            recent = self.micro.get_recent_micro_memories(
                limit=10,
                min_importance=4.0,
                apply_decay=True
            )

            for memory in recent:
                emotional = memory.get("emotional_context", {})
                current_importance = memory.get("current_importance", 0)

                if current_importance > 6.0 or emotional.get("emotional_intensity", 0) > 0.6:
                    topics = memory.get("topics", [])
                    return {
                        "summary": memory.get("summary", ""),
                        "topic": topics[0] if topics else "recent conversation",
                        "date": memory.get("created_at", "")[:10]
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to get recent open thread: {e}")
            return None

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    async def _generate_session_summary(self) -> str:
        """Generate a 2-3 sentence session summary using OpenAI."""
        try:
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in self.current_session_messages[-20:]
            ])

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Summarise this conversation in 2-3 sentences. "
                            "Focus on: main topics discussed, the user's emotional state, "
                            "and any key information shared. Be factual and brief."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Summarise this conversation:\n\n{conversation_text}"
                    }
                ],
                max_tokens=150,
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}")
            return f"Conversation with {len(self.current_session_messages)} messages"

    def _extract_session_emotions(self) -> Dict[str, Any]:
        """Simple keyword-based emotion extraction from session messages."""
        emotions: List[str] = []
        intensities: List[float] = []

        for msg in self.current_session_messages:
            if msg["role"] == "user":
                text = msg["content"].lower()
                if any(w in text for w in ["sad", "upset", "depressed", "down", "crying"]):
                    emotions.append("negative")
                    intensities.append(0.7)
                elif any(w in text for w in ["happy", "great", "excited", "wonderful", "good"]):
                    emotions.append("positive")
                    intensities.append(0.6)
                elif any(w in text for w in ["worried", "anxious", "nervous", "scared", "panic"]):
                    emotions.append("anxious")
                    intensities.append(0.7)

        if emotions:
            return {
                "primary_emotion": max(set(emotions), key=emotions.count),
                "emotional_intensity": sum(intensities) / len(intensities),
                "emotions_detected": list(set(emotions))
            }

        return {
            "primary_emotion": "neutral",
            "emotional_intensity": 0.0,
            "emotions_detected": []
        }

    def _extract_session_topics(self) -> List[str]:
        """Simple keyword-based topic extraction from user messages."""
        all_text = " ".join([
            msg["content"].lower()
            for msg in self.current_session_messages
            if msg["role"] == "user"
        ])

        topic_map = {
            "work":          ["work", "job", "career", "office", "project", "meeting"],
            "relationships": ["friend", "family", "partner", "relationship", "dating"],
            "health":        ["health", "doctor", "medicine", "exercise", "sleep"],
            "hobbies":       ["hobby", "game", "movie", "book", "music", "sport"],
            "emotions":      ["feel", "emotion", "mood", "anxiety", "depression"],
            "pets":          ["dog", "cat", "pet", "animal"],
            "goals":         ["goal", "plan", "dream", "ambition", "aspiration"],
            "values":        ["value", "important", "matter", "meaningful", "purpose"],
            "military":      ["service", "deployment", "veteran", "unit", "tour", "base"],
        }

        return [
            topic for topic, keywords in topic_map.items()
            if any(kw in all_text for kw in keywords)
        ]

    def _calculate_session_importance(
        self,
        emotional_context: Dict[str, Any],
        topics: List[str]
    ) -> float:
        """Score session importance 1-10 based on emotion and topic depth."""
        importance = 5.0

        if emotional_context["emotional_intensity"] > 0.5:
            importance += 2.0

        if "values" in topics:
            importance += 1.5

        if "military" in topics:
            importance += 1.0

        importance += min(len(topics) * 0.5, 2.0)

        if len(self.current_session_messages) > 20:
            importance += 1.0

        return min(importance, 10.0)

    # =========================================================================
    # STATS & CLEANUP
    # =========================================================================

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics across all memory tiers."""
        try:
            core_values = self.facts.get_fact("values", "core_values")
            has_values = isinstance(core_values, list) and len(core_values) > 0

            return {
                "persistent_facts": self.facts.get_stats(),
                "micro_memories": self.micro.get_stats(),
                "super_memories": self.consolidator.get_stats(),
                "current_session": {
                    "message_count": len(self.current_session_messages),
                    "duration_minutes": round(
                        (datetime.utcnow() - self.session_start_time).total_seconds() / 60, 1
                    )
                },
                "has_values": has_values,
                "values_count": len(core_values) if has_values else 0
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}

    def cleanup_old_data(self) -> Dict[str, int]:
        """Run cleanup on micro memory tier."""
        try:
            results = {
                "micro_memories_deleted": self.micro.cleanup_old_memories(days_threshold=60)
            }
            logger.info(f"Cleanup complete: {results}")
            return results
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {}
