# Data and Privacy Guidance

**This document is guidance, not legal advice.**
Your organisation must seek independent legal advice to ensure compliance
with applicable data protection law before deploying any AI tool to users.

---

## Who This Document Is For

Any organisation implementing this safety layer with real users, particularly
in the UK, EU, US, Canada, or Australia where data protection obligations
are significant.

---

## What Data This Codebase Handles

Depending on how you implement it, this codebase may process and store:

| Data Type | Where | Sensitivity |
|---|---|---|
| User messages | Firestore (encrypted) | Very high |
| Session summaries | Firestore (encrypted) | Very high |
| Emotional state metadata | Firestore (plaintext) | High |
| Topic tags | Firestore (plaintext) | Medium |
| Safety assessment logs | Application logs | High |
| User ID | Firestore | Medium |
| Timestamps | Firestore | Low |

All user message content and session summaries are encrypted at rest
using the encryption layer in `memory/micro_memory.py`.
Metadata (topics, emotional state labels, timestamps) is stored in plaintext
to enable Firestore queries.

**You must replace the encryption stubs in `micro_memory.py` with a real
encryption implementation before handling real user data.**

---

## UK and EU — GDPR Obligations

If you are based in the UK or EU, or serve users in the UK or EU,
UK GDPR / EU GDPR applies.

Key obligations relevant to this codebase:

### Lawful Basis
You must have a lawful basis for processing personal data.
For a voluntary support service, this is typically **consent** or
**legitimate interests**. Document your chosen basis before going live.

### Special Category Data
Mental health information is **special category data** under GDPR Article 9.
Processing it requires explicit consent or another Article 9 condition.
Veterans disclosing distress are sharing special category data.
This must be reflected in your privacy notice and data processing documentation.

### Data Minimisation
Only store what you need.
The memory consolidator is designed to store minimal long-term data.
Review what you are actually storing and delete what you do not need.

### Retention Policy
You must have a defined data retention policy.
Suggested minimum approach:
- Session micro memories: delete after 60 days if consolidated
- Super memories: review after 12 months
- Safety assessment logs: retain for safeguarding audit purposes,
  review after 12 months
- Implement `memory_manager.cleanup_old_data()` on a scheduled basis

### Right to Erasure
Users have the right to request deletion of their data.
You must be able to delete all data for a given `user_id` from Firestore.
Build and test this capability before going live.

### Privacy Notice
You must provide users with a clear privacy notice explaining:
- What data you collect
- Why you collect it
- How long you keep it
- Who has access to it
- How they can request deletion

### Data Processing Agreement
If you are using OpenAI's API to process user data, you must have
a Data Processing Agreement (DPA) in place with OpenAI.
See: https://openai.com/policies/data-processing-addendum

If you are using Firebase / Google Cloud, review Google's GDPR commitments:
See: https://cloud.google.com/privacy/gdpr

---

## US — HIPAA Considerations

If your organisation is a covered entity or business associate under HIPAA,
mental health conversation data may constitute Protected Health Information (PHI).

This codebase has not been designed or audited for HIPAA compliance.

If HIPAA applies to your organisation:
- Do not deploy this codebase without a HIPAA compliance review
- Ensure your cloud providers (Firebase, OpenAI) have BAAs in place
- Review logging practices — PHI must not appear in application logs

---

## Firestore Security Rules

Your Firestore database must have security rules that enforce
user-level data isolation.

At minimum, your rules should ensure:
- A user can only read and write their own documents
- No unauthenticated access to user data
- Admin access is restricted to authorised service accounts

Example minimum rules:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Users can only access their own data
    match /users/{userId}/{document=**} {
      allow read, write: if request.auth != null
                         && request.auth.uid == userId;
    }

    // Deny everything else by default
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

Test your rules using the Firebase Rules Playground before going live.

---

## OpenAI Data Handling

By default, OpenAI does not use API data to train models (as of March 2023).
However you should:

- Review OpenAI's current API data usage policy before deployment
- Ensure you have a DPA in place if serving EU/UK users
- Consider using OpenAI's zero data retention option if available
  for your tier
- Never send personally identifiable information in prompts
  beyond what is necessary

OpenAI API usage policy: https://openai.com/policies/api-usage-policies

---

## Encryption

This codebase includes encryption stubs in `memory/micro_memory.py`.

**You must replace these stubs with a real encryption implementation.**

Recommended approach for Python:
```python
from cryptography.fernet import Fernet

# Generate and store your key securely (e.g. in Secret Manager)
# Never hardcode keys in your codebase
key = Fernet.generate_key()
f = Fernet(key)

def encrypt_text(text: str) -> str:
    return f.encrypt(text.encode()).decode()

def decrypt_text(text: str) -> str:
    return f.decrypt(text.encode()).decode()
```

Store encryption keys in:
- Google Cloud Secret Manager (if using Firebase/GCP)
- AWS Secrets Manager
- Azure Key Vault
- Or equivalent — never in environment variables for production,
  never in your codebase

---

## Logging

The safety monitor writes to application logs when risk is detected.

Ensure your logging infrastructure:
- Does not write full message content to logs
  (the safety monitor logs keywords, not full messages — keep it that way)
- Has access controls restricting who can read logs
- Has a defined retention period
- Is reviewed regularly by a named person in your organisation

---

## Summary Checklist

Before going live with real users:

- [ ] Privacy notice written and accessible to users
- [ ] Lawful basis for processing documented
- [ ] Special category data handling documented
- [ ] DPA in place with OpenAI
- [ ] DPA in place with Google/Firebase
- [ ] Firestore security rules tested and live
- [ ] Encryption stubs replaced with real implementation
- [ ] Encryption keys stored in a secrets manager
- [ ] Data retention policy defined and implemented
- [ ] Right to erasure process built and tested
- [ ] Logging reviewed — no full message content in logs
- [ ] Independent legal review completed (UK/EU: GDPR, US: check HIPAA)

---

*This document is guidance only and does not constitute legal advice.
Your organisation is responsible for its own compliance obligations.*

*Last reviewed: February 2026*
*Maintained by: TheAIOldtimer / Zentrafuge project*
