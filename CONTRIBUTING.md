# Contributing to Veteran AI Safety Layer

First — thank you. This codebase exists to help veterans, and every
genuine improvement benefits every organisation using it.

Please read this before opening a pull request.

---

## Who Should Contribute

We welcome contributions from:

- Developers building veteran or military support tools
- Safeguarding professionals who spot gaps in the safety logic
- Clinicians or mental health practitioners who can improve the
  keyword coverage or persona principles
- Veterans with lived experience who can identify blind spots
- Anyone who finds a bug, gap, or unclear documentation

---

## What We Welcome

### Always welcome
- Additional country crisis resources in `safety/crisis_resources.py`
- Bug fixes with clear reproduction steps
- Documentation improvements
- New or improved tests
- Improved negation handling with evidence
- Non-English language keyword support
- Firestore security rule improvements

### Welcome with discussion first
- Changes to risk level thresholds
- Changes to escalation logic
- New keyword categories
- Changes to the memory architecture
- Changes to the persona principles

Open a GitHub Issue before writing code for any of the above.
Explain what you want to change and why. We will discuss it before
you invest time in a PR.

### Not accepted
- PRs that weaken safety detection thresholds without strong
  published evidence and prior discussion
- PRs that introduce external dependencies not already in
  `requirements.txt` without prior discussion
- PRs that add clinical or diagnostic language to persona principles
- PRs that remove or weaken the fail-safe behaviour in
  `safety_monitor.py`
- PRs that hardcode API keys, credentials, or environment-specific
  configuration

---

## The One Rule That Cannot Be Broken

> Do not weaken the fail-safe.

The safety monitor returns HIGH risk on any assessment error.
This is intentional. It is the most important line of code in
the repository. No PR that changes this behaviour will be merged
under any circumstances.

---

## How to Submit a PR on GitHub

Since this repo is maintained via the GitHub web interface:

1. **Fork the repository** using the Fork button top right
2. **Make your changes** in your fork
3. **Open a Pull Request** from your fork back to this repo
4. **Describe your changes** clearly:
   - What does this change?
   - Why is it needed?
   - What did you test?
   - For safety changes: what evidence supports this?

---

## Adding Crisis Resources

This is the most immediately useful contribution you can make.

To add a country to `safety/crisis_resources.py`:

1. Follow the existing structure exactly
2. Include veteran-specific resources where they exist
3. Verify every number is current before submitting
4. Include the URL for each resource
5. Note the date you verified the numbers in your PR description
6. Add your country code to the `get_available_countries()` return
   value — this happens automatically as it reads from the dict

Format:
```python
"XX": {
    "country": "Country Name",
    "emergency": "emergency number",
    "general_crisis": [
        {
            "name": "Organisation Name",
            "phone": "number or None",
            "text": "text instructions or None",
            "hours": "availability or None",
            "url": "https://...",
            "notes": "brief note"
        },
    ],
    "veteran_specific": [
        # same structure, or empty list if none exist
    ]
},
```

---

## Running Tests Before Submitting
```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run the test suite
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=safety --cov-report=term-missing
```

All existing tests must pass. If your change intentionally breaks
a test, explain why in your PR and include the updated test.

---

## On Safety Keyword Changes

If you believe a keyword should be added, changed, or removed:

1. Open an Issue first — do not submit a PR without discussion
2. Explain the specific case: what phrase, what false positive
   or false negative, what evidence
3. If you are a clinician or safeguarding professional, say so —
   your perspective carries significant weight here
4. Be aware that lowering sensitivity risks missing real crises.
   The bar for reducing detection is high. The bar for improving
   it is lower.

---

## On Negation Handling

False positives matter. We know the current negation handling is
not exhaustive. Improvements are welcome.

If you submit a negation improvement:
- Include new test cases that demonstrate the improvement
- Demonstrate it does not introduce new false negatives
  on the existing critical keyword list
- Keep the logic in `is_negated()` readable — this function
  will be reviewed by non-developers

---

## Code Style

- Python 3.11+
- Follow existing formatting — no reformatting PRs please
- Docstrings on all public methods
- Comments explain *why*, not *what*
- No emojis in production code (they exist in some legacy comments
  — we are gradually removing them)
- Log keywords and risk levels, never full message content

---

## A Note on Tone

This codebase is used by organisations supporting veterans in crisis.
Contributions are reviewed carefully and sometimes slowly. That is
intentional. We would rather take a week to review a safety change
properly than merge something that harms a veteran.

If your PR takes time to review, it is not being ignored.
It is being taken seriously.

---

*Maintained by TheAIOldtimer / Zentrafuge project*
*Open to collaboration with aligned veteran support organisations*
```

4. Commit message: `Add contributing guide`
5. Click **Commit changes**

---

That's the repo complete. Here's the full picture of what's now in there:

**Structure:**
```
├── LICENSE
├── README.md
├── ATTRIBUTION.md
├── SAFEGUARDING_DISCLAIMER.md
├── DATA_AND_PRIVACY.md
├── CONTRIBUTING.md
├── requirements.txt
├── requirements-dev.txt
├── safety/
│   ├── __init__.py
│   ├── safety_monitor.py
│   ├── emotion_tracker.py
│   └── crisis_resources.py
├── memory/
│   ├── __init__.py
│   ├── memory_manager.py
│   ├── micro_memory.py
│   └── memory_consolidator.py
├── persona/
│   └── CAEL_PERSONA_PRINCIPLES.md
├── docs/
│   └── INTEGRATION_NOTES.md
└── tests/
    └── test_safety_monitor.py
