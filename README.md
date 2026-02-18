# Veteran AI Safety Layer

Emotional safety guardrails, crisis detection logic, and memory optimisation
components built for veteran-facing AI companion applications.

Developed as part of the [Zentrafuge](https://github.com/TheAIOldtimer) project.

---

> ⚠️ **Before implementing this code, please read:**
> - [SAFEGUARDING_DISCLAIMER.md](./SAFEGUARDING_DISCLAIMER.md)
> - [DATA_AND_PRIVACY.md](./DATA_AND_PRIVACY.md)
>
> This is a tooling scaffold. It does not replace safeguarding policy,
> clinical oversight, or crisis services.

---

## What This Is

This repository contains safety-critical and memory components extracted
from a deployed veteran-focused AI companion application. It is offered
freely to veteran support organisations who are building AI-assisted tools
and need a solid foundation for emotional safety.

It is not a finished product. It is infrastructure — a starting point that
reflects real decisions made in a real deployment, shared so that other
organisations do not have to start from zero.

---

## What's Included

| Component | Description |
|---|---|
| `safety/safety_monitor.py` | Multi-level crisis detection with regex matching and negation handling |
| `safety/emotion_tracker.py` | Emotion parsing before persona response |
| `safety/crisis_resources.py` | Location-aware crisis line routing (UK, US, CA, AU, IE, NZ) |
| `memory/memory_manager.py` | Central memory orchestrator |
| `memory/micro_memory.py` | Session memory with 14-day forgetting curve |
| `memory/memory_consolidator.py` | Long-term pattern building from session summaries |
| `persona/CAEL_PERSONA_PRINCIPLES.md` | Trauma-informed AI persona design principles |
| `docs/INTEGRATION_NOTES.md` | Stack requirements and integration guidance |
| `DATA_AND_PRIVACY.md` | GDPR, Firestore rules, encryption, and retention guidance |
| `SAFEGUARDING_DISCLAIMER.md` | Responsibilities, limitations, and liability |

---

## Who This Is For

Veteran support organisations building AI companion or chat tools who need:

- Crisis detection logic with explainable escalation
- Safe messaging compliance built in from the start
- Memory systems that don't burn tokens unnecessarily
- A documented persona framework for trauma-informed AI

---

## What This Is Not

This codebase is not:

- A clinically validated mental health tool
- A regulated medical device
- A replacement for human safeguarding oversight
- A crisis service

Do not describe any implementation of this code as clinically validated
or regulated without independent verification.

---

## How the Safety Monitor Works

Detection runs in five phases on every message:
```
1. Normalise text        → lowercase, collapse whitespace, clean punctuation
2. Keyword matching      → regex with word boundaries (not naive substring)
3. Negation check        → skip matches preceded by negation context
4. Context multipliers   → substances / isolation / means / finality escalate risk
5. Emotional history     → persistent patterns escalate risk
```

Risk levels: `NONE → LOW → MEDIUM → HIGH → CRITICAL`

On any error, the system **fails safe** — it returns HIGH risk rather than
silently passing.

---

## Crisis Resource Routing

Crisis lines are configured per country in `safety/crisis_resources.py`.

Currently configured: **GB, US, CA, AU, IE, NZ**
```python
from safety.crisis_resources import format_crisis_message

msg = format_crisis_message(country_code='GB', prefer_veteran=True)
```

**Verify all numbers before deployment. Numbers change.**
Set a calendar reminder to check every six months.

---

## Call Order
```
User message
    → emotion_tracker.py      detect emotional state
    → safety_monitor.py       assess risk using emotional context
    → crisis_resources.py     route to appropriate support if needed
    → persona response        shaped by all of the above
```

Do not skip the emotion parse step. The safety monitor depends on it.

---

## Stack

Built with and tested on:

- Python 3.11+
- Flask 2.3.2
- OpenAI SDK 1.3.0
- Firebase Admin 6.2.0 / Firestore

Adaptable to other stacks — see `docs/INTEGRATION_NOTES.md`.

---

## Before You Deploy

Work through the checklists in:

- [`SAFEGUARDING_DISCLAIMER.md`](./SAFEGUARDING_DISCLAIMER.md) — safeguarding minimum viable checklist
- [`DATA_AND_PRIVACY.md`](./DATA_AND_PRIVACY.md) — data protection checklist

Neither list is long. Both matter.

---

## Known Limitations

- Keyword matching is rule-based. It will miss novel or unusual phrasing.
- Negation handling covers common patterns but is not exhaustive.
- Non-English input is not covered.
- Slang and code-switching are partially covered at best.
- This is a safety scaffold, not a clinical instrument.

If you find a gap, open a pull request. Every improvement benefits every
organisation using this layer.

---

## License

MIT — free to use, modify, and distribute with attribution.

This means anyone can use this code, including commercially. If that is
not your intention, review the license before sharing further.

There is no warranty. See LICENSE and SAFEGUARDING_DISCLAIMER.md.

---

## Attribution

If you use or adapt this code, please credit **Zentrafuge** and link back
to this repository.

See [ATTRIBUTION.md](./ATTRIBUTION.md).

---

## Contributing

Pull requests are welcome, particularly for:

- Additional country crisis resources
- Improved keyword coverage
- Better negation handling
- Non-English language support

Please do not submit PRs that weaken safety detection thresholds
without strong evidence and discussion first.

---

## Contact

Built by TheAIOldtimer as part of the Zentrafuge project.
Reach out via GitHub Issues.

We are open to collaboration with aligned veteran support organisations.
