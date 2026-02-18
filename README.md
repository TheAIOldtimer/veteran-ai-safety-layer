# Veteran AI Safety Layer

A set of emotional safety guardrails, crisis detection logic, and memory optimisation components built for veteran-facing AI companion applications.

Developed as part of the [Zentrafuge](https://github.com/TheAIOldtimer) project.

---

## What This Is

This repository contains the safety-critical and memory components extracted from a production veteran mental health AI system. It is offered freely to veteran support organisations who are building AI-assisted tools and need a solid foundation for emotional safety.

---

## What's Included

| Component | Description |
|---|---|
| `safety/safety_monitor.py` | Crisis detection, escalation logic, safe messaging compliance |
| `safety/emotion_tracker.py` | Emotion parsing before persona response |
| `memory/memory_manager.py` | Session and long-term memory management |
| `memory/micro_memory.py` | Lightweight in-session memory for token efficiency |
| `memory/memory_consolidator.py` | Prevents context window bloat over long sessions |
| `persona/CAEL_PERSONA_PRINCIPLES.md` | Design principles for trauma-informed AI persona |
| `docs/INTEGRATION_NOTES.md` | Stack requirements and integration guidance |

---

## Who This Is For

Veteran support organisations building AI companion or chat tools who need:
- Safe messaging compliance built in from the start
- Crisis escalation logic that doesn't over-pathologise
- Memory systems that don't burn tokens unnecessarily

---

## Stack

Built with and tested on:
- Python / Flask 2.3.2
- OpenAI SDK 1.3.0
- Firebase Admin 6.2.0 / Firestore

Adaptable to other stacks — see `docs/INTEGRATION_NOTES.md`.

---

## License

MIT — free to use, modify, and distribute. Attribution required. See LICENSE file.

---

## Attribution

If you use or adapt this code, please credit **Zentrafuge** and link back to this repository.

---

## Contact

Built by TheAIOldtimer. Reach out via GitHub Issues if you have questions or want to discuss integration.
