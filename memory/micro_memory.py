"""
Micro Memory - Session summaries with forgetting curve
Part of the Veteran AI Safety Layer
https://github.com/TheAIOldtimer/veteran-ai-safety-layer

Stores short conversation summaries in Firestore.
Importance decays over 14 days (half-life forgetting curve).
Older, low-importance memories are cleaned up automatically.

ENCRYPTION NOTE:
    This version has encryption stubbed out with plain passthrough functions.
    In production you should replace encrypt_text() and decrypt_text() with
    your own encryption implementation. Never store sensitive user content
    in plaintext in a production database.

STACK:
    Firebase Admin 6.2.0
    Firestore via firebase_admin.firestore
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from firebase_admin import firestore

logger = logging.getLogger(__name__)


# =============================================================================
# ENCRYPTION STUBS
# Replace these with your own encrypt/decrypt implementation in production.
# Options: Fernet (cryptography library), KMS, or your own key management.
# =============================================================================

def encrypt_text(text: str) -> str:
    """
    Stub: replace with real encryption in production.
    Example using Fernet:
        from cryptography.fernet import Fernet
        f = Fernet(your_key)
        return f.encrypt(text.encode()).decode()
    """
    return text


def decrypt_text(text: str) -> str:
    """
    Stub: replace with real decryption in production.
    Example using Fernet:
        from cryptography.fernet import Fernet
        f = Fernet(your_key)
        return f.decrypt(text.encode()).decode()
    """
    return text


# =============================================================================
# MICRO MEMORY
# =============================================================================

class MicroMemory:
    """
    Short conversation summaries with a forgetting curve.

    - Created at end of each session
    - Importance decays with a 14-day half-life
    - Consolidated memories are eligible for cleanup after 60 days
    - Sensitive content (summary, messages) is encrypted at rest

    Forgetting curve formula:
        I(t) = I₀ × (0.5) ^ (t / 14)
        Where t = days elapsed since creation
    """

    HALF_LIFE_DAYS = 14
    MIN_IMPORTANCE = 1.0

    def __init__(self, db: firestore.Client, user_id: str):
        self.db = db
        self.user_id = user_id
        self.collection_ref = (
            self.db.collection("users")
            .document(user_id)
            .collection("micro_memories")
        )

    # =========================================================================
    # CREATE
    # =========================================================================

    def create_micro_memory(
        self,
        summary: str,
        messages: List[Dict[str, str]],
        emotional_context: Dict[str, Any],
        topics: List[str],
        initial_importance: float = 5.0
    ) -> str:
        """
        Create a new micro memory from a conversation session.

        Args:
            summary:            Brief summary of the session (encrypted at rest)
            messages:           Session messages, up to 10 stored (encrypted at rest)
            emotional_context:  Emotional analysis dict from emotion_tracker
            topics:             Topics discussed this session
            initial_importance: Starting importance score 1-10 (default 5)

        Returns:
            memory_id of the created document
        """
        try:
            timestamp = datetime.utcnow()

            encrypted_messages = []
            for msg in messages[:10]:
                encrypted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": encrypt_text(msg.get("content", "")),
                    "timestamp": msg.get("timestamp", "")
                })

            micro_memory = {
                "user_id": self.user_id,
                "summary": encrypt_text(summary),
                "message_count": len(messages),
                "messages": encrypted_messages,
                "emotional_context": emotional_context,
                "topics": topics,
                "importance": initial_importance,
                "initial_importance": initial_importance,
                "created_at": timestamp.isoformat(),
                "last_accessed": timestamp.isoformat(),
                "access_count": 0,
                "consolidated": False,
                "type": "micro",
                "schema_version": 1
            }

            doc_ref = self.collection_ref.add(micro_memory)
            memory_id = doc_ref[1].id

            logger.info(
                f"Created micro memory {memory_id}: "
                f"{len(messages)} messages, "
                f"importance={initial_importance:.1f}, "
                f"emotion={emotional_context.get('primary_emotion', 'neutral')}"
            )

            return memory_id

        except Exception as e:
            logger.error(f"Failed to create micro memory: {e}")
            raise

    # =========================================================================
    # RETRIEVE
    # =========================================================================

    def get_micro_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific micro memory by ID, decrypted."""
        try:
            doc_ref = self.collection_ref.document(memory_id)
            doc = doc_ref.get()

            if not doc.exists:
                return None

            memory = doc.to_dict()
            memory["memory_id"] = memory_id
            memory["summary"] = decrypt_text(memory.get("summary", ""))

            if "messages" in memory:
                memory["messages"] = [
                    {
                        "role": msg.get("role", "user"),
                        "content": decrypt_text(msg.get("content", "")),
                        "timestamp": msg.get("timestamp", "")
                    }
                    for msg in memory["messages"]
                ]

            doc_ref.update({
                "last_accessed": datetime.utcnow().isoformat(),
                "access_count": firestore.Increment(1)
            })

            return memory

        except Exception as e:
            logger.error(f"Failed to get micro memory {memory_id}: {e}")
            return None

    def get_recent_micro_memories(
        self,
        limit: int = 20,
        min_importance: float = 1.0,
        apply_decay: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recent micro memories, sorted by decayed importance.

        Args:
            limit:          Max number of memories to return
            min_importance: Minimum importance after decay
            apply_decay:    Whether to apply forgetting curve

        Returns:
            List of decrypted memories, highest importance first
        """
        try:
            query = (
                self.collection_ref
                .where("consolidated", "==", False)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit * 2)
            )

            memories = []

            for doc in query.stream():
                memory = doc.to_dict()
                memory["memory_id"] = doc.id
                memory["summary"] = decrypt_text(memory.get("summary", ""))

                if "messages" in memory:
                    memory["messages"] = [
                        {
                            "role": msg.get("role", "user"),
                            "content": decrypt_text(msg.get("content", "")),
                            "timestamp": msg.get("timestamp", "")
                        }
                        for msg in memory["messages"]
                    ]

                if apply_decay:
                    memory["current_importance"] = self._calculate_decayed_importance(
                        memory["importance"],
                        memory["created_at"]
                    )
                else:
                    memory["current_importance"] = memory["importance"]

                if memory["current_importance"] >= min_importance:
                    memories.append(memory)

            memories.sort(key=lambda m: m["current_importance"], reverse=True)

            logger.info(f"Retrieved {len(memories)} micro memories for {self.user_id}")
            return memories[:limit]

        except Exception as e:
            logger.error(f"Failed to get recent micro memories: {e}")
            return []

    def search_by_emotion(
        self,
        emotion: str,
        limit: int = 10,
        min_intensity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search memories by emotional content."""
        try:
            query = (
                self.collection_ref
                .where("consolidated", "==", False)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(100)
            )

            matches = []

            for doc in query.stream():
                memory = doc.to_dict()
                emotional = memory.get("emotional_context", {})

                if (
                    emotional.get("primary_emotion") == emotion
                    and emotional.get("emotional_intensity", 0) >= min_intensity
                ):
                    memory["memory_id"] = doc.id
                    memory["summary"] = decrypt_text(memory.get("summary", ""))
                    memory["current_importance"] = self._calculate_decayed_importance(
                        memory["importance"],
                        memory["created_at"]
                    )
                    matches.append(memory)

                    if len(matches) >= limit:
                        break

            matches.sort(
                key=lambda m: m.get("emotional_context", {}).get("emotional_intensity", 0),
                reverse=True
            )

            return matches

        except Exception as e:
            logger.error(f"Failed to search by emotion '{emotion}': {e}")
            return []

    def search_by_topic(self, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memories by topic tag."""
        try:
            query = (
                self.collection_ref
                .where("topics", "array_contains", topic)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            memories = []
            for doc in query.stream():
                memory = doc.to_dict()
                memory["memory_id"] = doc.id
                memory["summary"] = decrypt_text(memory.get("summary", ""))
                memory["current_importance"] = self._calculate_decayed_importance(
                    memory["importance"],
                    memory["created_at"]
                )
                memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Failed to search by topic '{topic}': {e}")
            return []

    # =========================================================================
    # UPDATE
    # =========================================================================

    def boost_importance(self, memory_id: str, boost: float) -> bool:
        """Boost the importance score of a memory (capped at 10.0)."""
        try:
            doc_ref = self.collection_ref.document(memory_id)
            doc = doc_ref.get()

            if not doc.exists:
                return False
