# Integration Notes

This document explains the technical context this safety layer was built in, and what you need to know before adapting it to your own stack.

---

## Built On

| Dependency | Version |
|---|---|
| Python | 3.11+ |
| Flask | 2.3.2 |
| OpenAI SDK | 1.3.0 |
| Firebase Admin | 6.2.0 |
| Firestore | via `firebase_admin.firestore` |

---

## OpenAI SDK — Important

This codebase uses the **new** OpenAI SDK syntax:
```python
from openai import OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
```

Do **not** use the legacy `openai.ChatCompletion.create()` pattern. It will not work with SDK 1.3.0+.

---

## Firestore Initialisation
```python
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
```

All Firestore calls in this codebase follow this pattern. Never pass the client around as a global — initialise it once and reference via `firestore.client()`.

---

## Environment Variables

No API keys are hardcoded anywhere in this codebase. You will need:
```
OPENAI_API_KEY=your_key_here
FIREBASE_CREDENTIALS=path_or_json
FLASK_SECRET_KEY=your_secret_here
```

Store these in your environment or a `.env` file. Never commit them to GitHub.

---

## Emotion Parsing Flow

The intended call order is:
```
User message
    → emotion_tracker.py  (detect emotional state)
    → safety_monitor.py   (check for crisis signals)
    → persona response    (shaped by both outputs)
```

Do not skip the emotion parse step. The safety monitor depends on it.

---

## Memory Architecture

Two layers:

- **Session memory** (`micro_memory.py`) — lightweight, in-memory, lives for the conversation only. Keeps token usage low.
- **Long-term memory** (`memory_manager.py` + `memory_consolidator.py`) — Firestore-backed, stores minimal persistent facts only. Not a transcript store.

The consolidator runs at end-of-session to decide what, if anything, is worth keeping long term. This is intentional — storing everything is expensive and often harmful for users who don't want their worst moments permanently recorded.

---

## What You'll Need to Adapt

If you're on a different stack, the files that will need the most rework are:

- `memory_manager.py` — Firestore-specific, will need rewriting for your database
- `safety_monitor.py` — mostly portable, but check the logging calls reference your own user model
- `emotion_tracker.py` — fully portable, no external dependencies beyond OpenAI

---

## Questions

Open a GitHub Issue in this repo or contact via the Zentrafuge project.
