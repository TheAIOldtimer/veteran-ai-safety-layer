"""
Memory Consolidator - Consolidates micro memories into long-term super memories
Part of the Veteran AI Safety Layer
https://github.com/TheAIOldtimer/veteran-ai-safety-layer

How it works:
    Once a user has 10+ unconsolidated micro memories, the consolidator
    uses OpenAI to summarise them into a single super memory capturing
    themes, emotional arc, and value-related insights.

    micro memories (10) → OpenAI summary → super memory (1)

STACK:
    Firebase Admin 6.2.0
    OpenAI SDK 1.3.0  (from openai import OpenAI)

ENCRYPTION NOTE:
    Summary text is encrypted at rest using the stubs in micro_memory.py.
    Replace encrypt_text() / decrypt_text() with your own implementation.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from firebase_admin import firestore
from openai import OpenAI

from .micro_memory import encrypt_text, decrypt_text

logger = logging.getLogger(__name__)


class MemoryConsolidator:
    """
    Consolidates micro memories into super memories.

    Triggered automatically by MemoryManager.end_session() when
    unconsolidated micro memory count reaches CONSOLIDATION_THRESHOLD.

    Can also be triggered manually via MemoryManager.consolidate_session_memories().
    """

    CONSOLIDATION_THRESHOLD = 10

    def __init__(
        self,
        db: firestore.Client,
        user_id: str,
        openai_client: OpenAI
    ):
        self.db = db
        self.user_id = user_id
        self.openai_client = openai_client
        self.collection_ref = (
            self.db.collection("users")
            .document(user_id)
            .collection("super_memories")
        )

    # =========================================================================
    # CONSOLIDATION TRIGGER
    # =========================================================================

    def check_consolidation_ready(self, micro_memory) -> bool:
        """
        Returns True if there are enough unconsolidated micro memories
        to warrant a consolidation pass.
        """
        count = micro_memory.get_unconsolidated_count()
        return count >= self.CONSOLIDATION_THRESHOLD

    async def consolidate_memories(self, micro_memory) -> Optional[str]:
        """
        Consolidate unconsolidated micro memories into a super memory.

        Args:
            micro_memory: MicroMemory instance

        Returns:
            super_memory_id or None if consolidation did not run
        """
        try:
            memories_to_consolidate = micro_memory.get_recent_micro_memories(
                limit=self.CONSOLIDATION_THRESHOLD,
                min_importance=2.0,
                apply_decay=False
            )

            if len(memories_to_consolidate) < self.CONSOLIDATION_THRESHOLD:
                logger.info(
                    f"Not enough micro memories to consolidate "
                    f"({len(memories_to_consolidate)}/{self.CONSOLIDATION_THRESHOLD})"
                )
                return None

            logger.info(
                f"Starting consolidation of "
                f"{len(memories_to_consolidate)} micro memories "
                f"for user {self.user_id}"
            )

            consolidation = await self._generate_consolidation(memories_to_consolidate)

            if not consolidation:
                logger.error("Failed to generate consolidation")
                return None

            super_memory_id = self._create_super_memory(
                consolidation,
                memories_to_consolidate
            )

            for memory in memories_to_consolidate:
                micro_memory.mark_as_consolidated(memory["memory_id"])

            logger.info(f"Consolidation complete: super memory {super_memory_id}")
            return super_memory_id

        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            return None

    # =========================================================================
    # OPENAI CONSOLIDATION
    # =========================================================================

    async def _generate_consolidation(
        self,
        micro_memories: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Use OpenAI to generate a consolidated summary of micro memories.
        Micro memories are already decrypted at this point.
        """
        try:
            prompt = self._build_consolidation_prompt(micro_memories)

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a memory consolidation system for a veteran support "
                            "AI companion. Analyse these conversation summaries and extract:\n"
                            "1. Recurring themes and patterns\n"
                            "2. Significant life events or changes\n"
                            "3. Emotional patterns and how they evolved over time\n"
                            "4. Key facts and preferences\n"
                            "5. Value-related insights — what clearly matters to this person\n"
                            "6. Unresolved concerns or ongoing threads\n\n"
                            "Be factual, concise, and respectful. "
                            "Do not diagnose or pathologise. "
                            "Write as if briefing a trusted support person, not a clinician."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=600,
                temperature=0.3
            )

            consolidation_text = response.choices[0].message.content

            return {
                "summary":            consolidation_text,
                "themes":             self._extract_themes(micro_memories),
                "topics":             self._extract_topics(micro_memories),
                "emotional_patterns": self._extract_emotional_patterns(micro_memories),
                "emotional_arc":      self._analyze_emotional_arc(micro_memories),
                "value_insights":     self._extract_value_insights(micro_memories),
                "source_memory_count": len(micro_memories)
            }

        except Exception as e:
            logger.error(f"Failed to generate consolidation: {e}")
            return None

    def _build_consolidation_prompt(
        self,
        micro_memories: List[Dict[str, Any]]
    ) -> str:
        """Build the prompt sent to OpenAI for consolidation."""
        lines = [
            f"Consolidate these {len(micro_memories)} conversation summaries "
            f"into a single coherent overview:\n"
        ]

        for i, memory in enumerate(micro_memories, 1):
            lines.append(f"\n=== Session {i} ===")
            lines.append(f"Date: {memory['created_at'][:10]}")
            lines.append(f"Summary: {memory['summary']}")
            lines.append(f"Topics: {', '.join(memory.get('topics', []))}")

            emotional = memory.get("emotional_context", {})
            if emotional:
                lines.append(
                    f"Emotion: {emotional.get('primary_emotion', 'neutral')} "
                    f"(intensity: {emotional.get('emotional_intensity', 0):.1f})"
                )

        lines.append("\n\nYour consolidated overview should cover:")
        lines.append("- Main themes and recurring patterns")
        lines.append("- Emotional journey across this period")
        lines.append("- Key topics of importance")
        lines.append("- What this person clearly values")
        lines.append("- Any unresolved threads worth following up")

        return "\n".join(lines)

    # =========================================================================
    # PATTERN EXTRACTION
    # =========================================================================

    def _extract_themes(self, micro_memories: List[Dict[str, Any]]) -> List[str]:
        """Extract themes that appear across multiple micro memories."""
        theme_keywords = {
            "personal_growth":   ["growth", "learning", "change", "progress", "development"],
            "relationships":     ["friend", "family", "partner", "relationship", "connection"],
            "work_career":       ["work", "job", "career", "project", "professional"],
            "health_wellness":   ["health", "exercise", "wellness", "sleep", "fitness"],
            "emotions":          ["feeling", "emotion", "mood", "stress", "anxiety"],
            "hobbies_interests": ["hobby", "interest", "passion", "enjoy", "creative"],
            "values_meaning":    ["value", "important", "matter", "meaningful", "purpose"],
            "challenges":        ["difficult", "struggle", "challenge", "hard", "problem"],
            "achievements":      ["achieve", "accomplish", "success", "proud", "milestone"],
            "military_service":  ["service", "deployment", "veteran", "unit", "tour", "mission"],
        }

        theme_counts: Dict[str, int] = {}

        for memory in micro_memories:
            summary_lower = memory["summary"].lower()
            for theme, keywords in theme_keywords.items():
                if any(kw in summary_lower for kw in keywords):
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1

        return [theme for theme, count in theme_counts.items() if count >= 2]

    def _extract_topics(self, micro_memories: List[Dict[str, Any]]) -> List[str]:
        """Extract and rank topics by frequency across micro memories."""
        topic_counts: Dict[str, int] = {}

        for memory in micro_memories:
            for topic in memory.get("topics", []):
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, _ in sorted_topics[:10]]

    def _extract_emotional_patterns(
        self,
        micro_memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Summarise emotional patterns across the consolidation period."""
        emotions: List[str] = []
        intensities: List[float] = []

        for memory in micro_memories:
            emotional = memory.get("emotional_context", {})
            if emotional:
                emotions.append(emotional.get("primary_emotion", "neutral"))
                intensities.append(emotional.get("emotional_intensity", 0.0))

        if not emotions:
            return {}

        emotion_counts: Dict[str, int] = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        return {
            "dominant_emotion":    max(emotion_counts.items(), key=lambda x: x[1])[0],
            "average_intensity":   sum(intensities) / len(intensities),
            "emotion_distribution": emotion_counts
        }

    def _analyze_emotional_arc(
        self,
        micro_memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyse how emotional tone evolved across the consolidation period.
        Divides memories into thirds and compares beginning vs end.
        """
        try:
            if len(micro_memories) < 3:
                return {}

            sorted_memories = sorted(micro_memories, key=lambda m: m["created_at"])
            third = max(len(sorted_memories) // 3, 1)

            beginning = sorted_memories[:third]
            middle    = sorted_memories[third:2 * third]
            end       = sorted_memories[2 * third:]

            def period_emotion(memories):
                emotions = []
                intensities = []
                for m in memories:
                    em = m.get("emotional_context", {})
                    if em:
                        emotions.append(em.get("primary_emotion", "neutral"))
                        intensities.append(em.get("emotional_intensity", 0))
                if not emotions:
                    return {"emotion": "neutral", "intensity": 0.0}
                return {
                    "emotion":   max(set(emotions), key=emotions.count),
                    "intensity": sum(intensities) / len(intensities)
                }

            arc = {
                "beginning": period_emotion(beginning),
                "middle":    period_emotion(middle),
                "end":       period_emotion(end)
            }

            diff = arc["end"]["intensity"] - arc["beginning"]["intensity"]
            arc["trend"] = "intensifying" if diff > 0.2 else "calming" if diff < -0.2 else "stable"

            logger.info(
                f"Emotional arc for {self.user_id}: "
                f"{arc['beginning']['emotion']} → {arc['end']['emotion']} "
                f"({arc['trend']})"
            )

            return arc

        except Exception as e:
            logger.error(f"Failed to analyse emotional arc: {e}")
            return {}

    def _extract_value_insights(
        self,
        micro_memories: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract sentences from summaries that reference values or meaning."""
        value_keywords = [
            "important", "matter", "value", "meaningful", "purpose",
            "belief", "principle", "care about", "stand for"
        ]

        insights = []

        for memory in micro_memories:
            summary = memory.get("summary", "")
            for sentence in summary.split("."):
                if any(kw in sentence.lower() for kw in value_keywords):
                    cleaned = sentence.strip()
                    if cleaned:
                        insights.append(cleaned)
                    break

        return list(set(insights))[:5]

    # =========================================================================
    # FIRESTORE WRITE
    # =========================================================================

    def _create_super_memory(
        self,
        consolidation: Dict[str, Any],
        source_memories: List[Dict[str, Any]]
    ) -> str:
        """Write the super memory document to Firestore."""
        try:
            timestamp = datetime.utcnow()

            super_memory = {
                "user_id":             self.user_id,
                "summary":             encrypt_text(consolidation["summary"]),
                "themes":              consolidation["themes"],
                "topics":              consolidation["topics"],
                "emotional_patterns":  consolidation["emotional_patterns"],
                "emotional_arc":       consolidation.get("emotional_arc", {}),
                "value_insights":      consolidation.get("value_insights", []),
                "source_memory_count": len(source_memories),
                "source_memory_ids":   [m["memory_id"] for m in source_memories],
                "date_range": {
                    "start": source_memories[-1]["created_at"],
                    "end":   source_memories[0]["created_at"]
                },
                "created_at":     timestamp.isoformat(),
                "last_accessed":  timestamp.isoformat(),
                "access_count":   0,
                "importance":     7.0,
                "type":           "super",
                "schema_version": 1
            }

            doc_ref = self.collection_ref.add(super_memory)
            super_memory_id = doc_ref[1].id

            logger.info(f"Created super memory {super_memory_id}")
            return super_memory_id

        except Exception as e:
            logger.error(f"Failed to create super memory: {e}")
            raise

    # =========================================================================
    # RETRIEVAL
    # =========================================================================

    def get_super_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific super memory by ID, decrypted."""
        try:
            doc_ref = self.collection_ref.document(memory_id)
            doc = doc_ref.get()

            if not doc.exists:
                return None

            memory = doc.to_dict()
            memory["memory_id"] = memory_id
            memory["summary"] = decrypt_text(memory.get("summary", ""))

            doc_ref.update({
                "last_accessed": datetime.utcnow().isoformat(),
                "access_count":  firestore.Increment(1)
            })

            return memory

        except Exception as e:
            logger.error(f"Failed to get super memory {memory_id}: {e}")
            return None

    def get_all_super_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all super memories for this user, decrypted, newest first."""
        try:
            query = (
                self.collection_ref
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            memories = []
            for doc in query.stream():
                memory = doc.to_dict()
                memory["memory_id"] = doc.id
                memory["summary"] = decrypt_text(memory.get("summary", ""))
                memories.append(memory)

            logger.info(f"Retrieved {len(memories)} super memories for {self.user_id}")
            return memories

        except Exception as e:
            logger.error(f"Failed to get super memories: {e}")
            return []

    def search_by_theme(self, theme: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search super memories by theme tag."""
        try:
            query = (
                self.collection_ref
                .where("themes", "array_contains", theme)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            memories = []
            for doc in query.stream():
                memory = doc.to_dict()
                memory["memory_id"] = doc.id
                memory["summary"] = decrypt_text(memory.get("summary", ""))
                memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Failed to search by theme '{theme}': {e}")
            return []

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about super memories."""
        try:
            total = 0
            themes_count: Dict[str, int] = {}
            has_arc = 0
            has_values = 0

            for doc in self.collection_ref.limit(100).stream():
                total += 1
                memory = doc.to_dict()

                for theme in memory.get("themes", []):
                    themes_count[theme] = themes_count.get(theme, 0) + 1

                if memory.get("emotional_arc"):
                    has_arc += 1
                if memory.get("value_insights"):
                    has_values += 1

            return {
                "total_super_memories": total,
                "top_themes": sorted(
                    themes_count.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "with_emotional_arc":   has_arc,
                "with_value_insights":  has_values
            }

        except Exception as e:
            logger.error(f"Failed to get super memory stats: {e}")
            return {}
