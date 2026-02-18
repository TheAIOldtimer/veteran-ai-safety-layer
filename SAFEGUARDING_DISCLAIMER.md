# Safeguarding Disclaimer

**Please read this before implementing any part of this codebase.**

---

## What This Is

This repository contains open-source tooling components — a safety detection
layer, a memory system, and a persona design framework — developed for use in
a veteran-facing AI companion application.

It is offered freely to aligned veteran support organisations in good faith,
as a starting point for building safer AI tools.

---

## What This Is Not

This codebase is **not**:

- A clinically validated mental health intervention
- A regulated medical device
- A crisis service
- A replacement for human safeguarding oversight
- A guarantee of user safety

It has not undergone formal clinical validation, regulatory approval,
or independent safeguarding audit.

---

## Your Responsibilities as an Implementing Organisation

By using this code, your organisation accepts full responsibility for:

1. **Safeguarding policy** — You must have a safeguarding policy in place
   that governs how your AI tool handles user distress. This code does not
   provide that policy.

2. **Crisis pathway implementation** — The safety monitor detects risk and
   flags intervention types. It does not automatically contact emergency
   services or crisis lines. You are responsible for defining and implementing
   what happens after a flag is raised.

3. **Local crisis resources** — Crisis line numbers and emergency services
   vary by country. You must configure and verify crisis resources appropriate
   to your user base. See `safety/crisis_resources.py` for the routing
   abstraction.

4. **Clinical oversight** — Any AI tool deployed to vulnerable populations,
   including veterans, should be developed and monitored with appropriate
   clinical or safeguarding oversight. This code does not substitute for that.

5. **Data protection compliance** — You are responsible for ensuring your
   implementation complies with applicable data protection law (GDPR, UK GDPR,
   HIPAA, PIPEDA, or equivalent). See `DATA_AND_PRIVACY.md` for guidance.

6. **Staff training** — Teams deploying AI tools to vulnerable users should
   be trained in trauma-informed practice and basic safeguarding awareness.

7. **Testing before deployment** — You must test this code thoroughly in your
   own environment before deploying it to real users. Edge cases exist. See
   the known limitations section of `safety/safety_monitor.py`.

---

## Liability

This code is provided under the MIT licence, which means:

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

The author(s) of this repository:

- Are not liable for harm arising from implementation or misuse of this code
- Do not warrant that this code will detect all instances of user distress
- Do not warrant that this code is suitable for any particular deployment context
- Are not responsible for your organisation's safeguarding decisions

---

## Minimum Viable Safeguarding Checklist

Before going live with any implementation of this code, your organisation
should be able to answer **yes** to all of the following:

- [ ] We have a named safeguarding lead who has reviewed this implementation
- [ ] We have defined what happens when the safety monitor raises a HIGH or CRITICAL flag
- [ ] We have verified the crisis resources configured for our user base
- [ ] We have a process for reviewing safety logs regularly
- [ ] We have informed users that this is an AI tool, not a human
- [ ] We have a process for users to reach a human if needed
- [ ] We have reviewed our data retention and privacy obligations
- [ ] We have tested edge cases in the safety monitor before deployment

---

## Good Faith Clause

This code is shared in good faith with organisations who are trying to help
veterans. If you find a bug, a gap, or an improvement — please open a pull
request or raise a GitHub Issue. Every improvement benefits every organisation
using this layer.

We are open to collaboration. We are not open to misrepresentation.
Please do not describe this tooling as "clinically validated," "NHS-approved,"
"VA-approved," or any equivalent without independent verification.

---

*Last reviewed: February 2026*
*Maintained by: TheAIOldtimer / Zentrafuge project*
