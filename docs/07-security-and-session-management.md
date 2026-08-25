# Nursilo — Security and Session Management

| Field | Value |
| --- | --- |
| Document | `07-security-and-session-management.md` |
| Version | `1.0.0` |
| Status | **Approved** — locked security specification |
| Product | Nursilo |
| Depends on | [`03-user-roles.md`](03-user-roles.md), [`04-system-architecture.md`](04-system-architecture.md), [`06-database-design.md`](06-database-design.md) (Approved v1.0.0; **unchanged by this document**) |
| Purpose | Security specification for authentication, sessions, devices, account protection, and operational security (Version 1) |
| Out of scope | Django models, migrations, SQL, API endpoints, implementation code, UI implementation |
| Nature | **Additive only** — does not modify locked docs `00`–`06` |

---

## 1. Purpose

This document defines the **complete security architecture** for Nursilo Version 1 in the areas of:

- Authentication security  
- Session management  
- Device management  
- Account protection  
- Login security  
- Password security  
- Operational security  
- Future MFA support (reserved; not shipped in V1 product features)

It is a **SECURITY SPECIFICATION ONLY**. It complements—without modifying—the approved:

| Document | Relationship |
| --- | --- |
| [`03-user-roles.md`](03-user-roles.md) | RBAC and least-privilege boundaries this document must respect |
| [`04-system-architecture.md`](04-system-architecture.md) | AuthN/AuthZ layering, secure HTTP posture, service-layer enforcement |
| [`06-database-design.md`](06-database-design.md) | Logical persistence expectations (no schema rewrite here) |

Database design remains locked. Any future session/device tables must align with `06` via a separate approved change—not by editing `06` from this draft.

---

## 2. Security Principles

| Principle | Meaning for Nursilo |
| --- | --- |
| **Defense in Depth** | Edge (Cloudflare/TLS), application authN/authZ, entitlements, and audit reinforce each other |
| **Least Privilege** | Roles and session capabilities follow `03-user-roles.md`; no ambient “staff” bypass |
| **Fail Closed** | Missing session, failed auth, or failed entitlement → deny |
| **Server-side Authorization** | UI hiding is not security; services enforce RBAC + entitlements |
| **Session Security** | Sessions are server-validated, bound to policy limits, and revocable |
| **Zero Trust (practical)** | Every request re-establishes identity + session validity; do not trust client claims alone |
| **Secure Defaults** | HTTPS, secure cookies, CSRF, strong hashing, conservative timeouts |
| **Auditability** | Security-relevant actions produce durable audit/security events |
| **Privacy by Design** | Collect minimal device/context data needed for account protection |
| **OWASP Best Practices** | Align controls with common web risks (injection, XSS, CSRF, auth abuse, session fixation) |

---

## 3. Authentication Model

| Concern | V1 specification |
| --- | --- |
| **Primary credentials** | Email + password for individual accounts |
| **Password storage** | Secure one-way password hashing only; never store reversible passwords |
| **Password reset** | Time-limited, one-time recovery tokens delivered out-of-band (email) |
| **Web authentication** | Server-side **session** authentication for Django Templates + HTMX |
| **Cookies** | Session cookies marked **Secure**, **HttpOnly**, and appropriate **SameSite** |
| **Transport** | **HTTPS only** in production (Cloudflare edge → origin posture per architecture) |
| **CSRF** | Required for cookie-authenticated state-changing requests |
| **Future mobile** | Token-based authentication adapter for Flutter calling the same Account / Access / Entitlement services (not a second security model) |

Authentication establishes **who** the principal is. Authorization remains RBAC + entitlements + domain policy as defined in architecture and roles docs.

### 3.1 CSRF clarification

| Rule | Specification |
| --- | --- |
| State-changing requests | CSRF protection is required for authenticated state-changing requests |
| Safe methods | GET requests remain safe and idempotent |
| HTMX | HTMX interactions follow the same CSRF policy as ordinary form/authenticated mutations |
| Complement | CSRF complements authentication and authorization; it does not replace them |

---

## 4. Concurrent Device Session Policy

**Required V1 policy.**

### 4.1 Maximum concurrent sessions

| Setting | Value |
| --- | --- |
| **Maximum concurrent active sessions** | **3** |
| Typical device mix | Mobile, Laptop/Desktop, Tablet |

### 4.2 Business rules

| Rule | Specification |
| --- | --- |
| Cap | A user may hold at most **3 active sessions** at once |
| Fourth login | Behavior is **configurable** by Super Admin security settings: **(A) Reject login**, or **(B) Automatically terminate the oldest active session** then allow the new login |
| Validation | Session validity is evaluated **server-side** on authenticated requests |
| Device logout | User may revoke a single selected session/device |
| Logout all devices | User may revoke all sessions (typically retaining or re-establishing current session per UX policy; security default should leave the user explicitly re-authenticated on current device only) |
| Password reset | Invalidates **all other** active sessions |
| Password change | Invalidates **all other** active sessions |
| Super Admin | May revoke all sessions for a user (and platform-wide emergency controls per §17) |
| Cleanup | Expired/inactive sessions are cleaned automatically by scheduled or request-adjacent maintenance |

### 4.3 Rationale

Three concurrent sessions balance real student device usage (phone + computer + tablet) against credential sharing and session sprawl risk.

### 4.4 Device limit exceptions

| Rule | Specification |
| --- | --- |
| Default | The maximum remains **3** active sessions for learners and standard accounts |
| Exceptions | Super Admin may configure higher concurrent-session exceptions only for **QA accounts**, **internal testing**, and **emergency operational accounts** |
| Audit | Every exception grant, change, or removal is audit-logged |
| Scope | Exceptions do **not** change the default learner policy |

---

## 5. Device Management

### 5.1 Device Management page (product surface)

Learners (and staff for their own accounts) receive a **Device Management** view listing active sessions/devices.

### 5.2 Visible fields (per session/device)

| Field | Purpose |
| --- | --- |
| Device name | Human-readable label |
| Browser | Parsed browser family/name |
| Operating System | Parsed OS |
| IP address | Network origin of session |
| Country | Derived geo hint when available |
| Last active time | Last successful authenticated activity |
| Login time | Session creation / login time |
| Current device indicator | Marks the session serving this request |

### 5.3 Student actions

| Action | V1 / Future |
| --- | --- |
| Logout one device | **V1** |
| Logout all devices | **V1** |
| Rename trusted device | **Future** (pairs with trusted devices §13) |

Device Management must not expose secrets (password hashes, raw tokens, payment credentials).

### 5.4 Device naming guidance

Device names are initially generated automatically from available browser/OS signals.

| Example auto-generated name |
| --- |
| Chrome on Windows |
| Firefox on Linux |
| Safari on iPhone |

**Future:** Users may rename devices (aligned with rename trusted device capability).

### 5.5 Country geolocation disclaimer

Country information shown in Device Management:

| Clarification | Specification |
| --- | --- |
| Source | Derived from IP geolocation |
| Accuracy | Approximate only |
| Limitations | May be inaccurate because of VPNs, proxies, carrier routing, or similar technologies |

---

## 6. Logical Session Model

Logical entity only (not SQL, not Django models):

### 6.1 `UserSession`

| Conceptual field | Meaning |
| --- | --- |
| Session ID | Opaque server session identifier |
| User | Owning `UserAccount` identity |
| Device ID | Stable-enough device key for grouping (non-invasive; not invasive fingerprinting) |
| Device Name | Display label |
| Browser | Browser metadata |
| Operating System | OS metadata |
| IP Address | Last/known IP for the session |
| Country | Optional geo derivation |
| User Agent | Raw UA for support/audit (store carefully; display parsed fields to users) |
| Created Time | Login / session start |
| Last Activity | Sliding activity marker for idle timeout |
| Expiration Time | Absolute and/or computed expiry boundary |
| Active Status | Active / revoked / expired |

Services use `UserSession` records to enforce the **3-session cap**, device logout, and admin revoke. Persistence mapping is deferred; must not silently rewrite locked `06` without a future approved DB addendum.

### 6.2 Session fixation protection

| Rule | Specification |
| --- | --- |
| Post-authentication | Session identifiers must be regenerated after successful authentication |
| Privilege change | Session identifiers should also be regenerated after privilege changes (for example, role elevation) |
| Intent | Prevent session fixation attacks |
| Scope | Conceptual security requirement only; no implementation details in this document |

### 6.3 Secure session identifiers

| Rule | Specification |
| --- | --- |
| Strength | Session identifiers must be cryptographically secure |
| Unpredictability | Identifiers must be unpredictable |
| Exposure | Never exposed unnecessarily to clients or third parties beyond normal cookie transport |
| Logging | Never logged in plaintext |

### 6.4 Session revocation propagation

| Rule | Specification |
| --- | --- |
| Effectiveness | Session revocation should become effective immediately or as close to immediate as practical |
| Validation | Revoked sessions must fail **server-side** validation |
| Client state | Browser state alone must never determine whether a session remains valid |
| Consistency | Session revocation applies consistently across all active devices |

### 6.5 Session cookie / identifier rotation

| Rule | Specification |
| --- | --- |
| Rotate after | Successful authentication; password change; privilege elevation; other security-sensitive transitions |
| Purpose | Reduce session fixation and session hijacking risk |

### 6.6 Device vs session terminology

| Term | Meaning |
| --- | --- |
| **Device** | Physical hardware (phone, laptop, tablet) |
| **Session** | A single authenticated browser or app session |

**Example:** Chrome and Firefox on the same laptop represent **two separate sessions**, even though they may share one physical device.

This distinction avoids ambiguity when applying the concurrent-session cap and Device Management actions.

---

## 7. Login Security

| Control | Specification |
| --- | --- |
| Failed login handling | Record failure events; generic user-facing messages (avoid account enumeration where practical) |
| Brute-force protection | Limit rapid password guessing per account and/or network identity |
| Login throttling | Rate-limit login attempts |
| Progressive delays | Increase delay after repeated failures |
| Temporary account lock | Temporary lockout after threshold failures; recoverable via time expiry and/or password reset |
| Password reset limits | Rate-limit reset requests to reduce abuse and email flooding |

### 7.1 Future

| Control | Timing |
| --- | --- |
| CAPTCHA / bot challenges | Future (after abuse patterns justify) |

### 7.2 Account lock policy

Multiple failed login attempts trigger progressive protection. Thresholds remain **configurable by Super Admin**. Exact implementation is intentionally unspecified.

| Example conceptual threshold | Example outcome |
| --- | --- |
| **5** failed attempts | Temporary lock for approximately **15 minutes** |
| Repeated failures after unlock / continued abuse | Longer lock duration |

| Recovery | Specification |
| --- | --- |
| Time expiry | Lock ends when the configured duration elapses |
| Password reset | May immediately recover the account (subject to reset success and rate limits) |

### 7.3 Rate limiting scope

Throttling and progressive protection may consider one or more of the following signals:

- User account  
- IP address  
- Device  
- Combined signals  

Thresholds remain configurable by Super Admin.

---

## 8. Password Policy

| Requirement | V1 rule |
| --- | --- |
| Minimum length | Enforce a strong minimum length appropriate for web accounts (platform-configured; must not be trivially short) |
| Uppercase | Require at least one uppercase letter |
| Lowercase | Require at least one lowercase letter |
| Number | Require at least one digit |
| Special character | Require at least one special character |
| Common passwords | Reject known-common / breached-common passwords where feasible |
| Reused passwords | **Future** — prevent reuse of recent passwords |
| Reset tokens | High-entropy, single-use, short-lived |
| Password expiry | **Not required** for learners in V1 |

Password change and reset both trigger session invalidation rules in §4 and §9.

### 8.1 Password history (Future)

**Future only — not implemented in Version 1.**

| Capability | Intent |
| --- | --- |
| Prevent reuse | Block reuse of recent passwords |
| History length | Configurable by Super Admin security policy when introduced |

### 8.2 Password strength guidance

Besides complexity requirements, Nursilo encourages:

| Guidance | Intent |
| --- | --- |
| Long passphrases | Prefer longer secrets that are easier to remember and harder to guess |
| Length over complexity alone | Password length generally provides stronger protection than complexity rules alone |
| Avoid predictable substitutions | Discourage patterns such as obvious letter-to-number substitutions |
| Password managers | Encourage use of a reputable password manager |

Conceptual guidance only.

---

## 9. Session Lifecycle

```text
Login → Authenticated → Active
              │
              ├── Idle timeout → Expired / Forced re-auth
              ├── Absolute timeout → Expired
              ├── Logout (self) → Revoked
              ├── Device logout / Logout all → Revoked
              ├── Password reset / Password change → Other sessions revoked
              ├── Admin / Super Admin revoke → Revoked
              └── Forced logout (policy) → Revoked
```

| State / event | Meaning |
| --- | --- |
| Login | Credentials verified; new `UserSession` created within concurrent-session policy |
| Authenticated | Principal identity established for the request |
| Active | Session valid; last activity updated on use |
| Idle timeout | No activity within idle window → session no longer accepted |
| Expiration | Absolute lifetime reached |
| Logout | User-initiated end of current (or selected) session |
| Forced logout | Policy or admin terminates session(s) |
| Password reset | Recovery completes; sessions invalidated per §4 |
| Password change | Authenticated change; sessions invalidated per §4 |
| Admin revoke | Privileged termination of user sessions |

---

## 10. Session Timeout Policy

| Timeout | Recommendation (V1) |
| --- | --- |
| **Idle timeout** | **30 minutes** without authenticated activity |
| **Absolute timeout** | **30 days** maximum session lifetime (whichever bound hits first ends the session) |
| **Remember Me** | Optional **Future** feature; not a V1 requirement |

Timeouts are enforced server-side. Client-side timers are UX aids only.

### 10.1 Session expiry warning

| Rule | Specification |
| --- | --- |
| Warning | Before idle timeout, users should receive a warning notification |
| Default recommendation | Show the warning approximately **5 minutes** before session expiration due to idle timeout |
| Activity | Any authenticated activity may extend the idle timeout according to session policy |
| Authority | This warning is a **UX enhancement only**; **server-side timeout enforcement remains authoritative** |

### 10.2 Session refresh policy

| Rule | Specification |
| --- | --- |
| Idle refresh | Authenticated activity refreshes the **idle** timeout |
| Absolute lifetime | Activity does **not** extend the **absolute** session lifetime |
| Authority | Absolute timeout remains authoritative |
| After expiry | Expired sessions always require re-authentication |

### 10.3 Remember Me (Future) clarification

| Rule | Specification |
| --- | --- |
| V1 | **Not included** in Version 1 |
| Future approach | May use persistent secure cookies |
| Absolute bound | Must respect maximum absolute session lifetime |
| Session cap | Must **not** bypass the maximum concurrent session cap |

---

## 11. Login History

Logical **Login History** (append-oriented security/support record; distinct from day-to-day `UserSession` list UX though may share sources).

### 11.1 Stored facts (conceptual)

| Field | Meaning |
| --- | --- |
| Login time | When the attempt occurred |
| Logout time | When known (nullable for failures/abrupt expiry) |
| Success / Failure | Outcome |
| Device | Device label/id if known |
| Browser | Browser metadata |
| Country | Geo hint if available |
| IP | Source IP |
| User Agent | UA string / parsed summary |

### 11.2 Learner access

Students may view **recent login history** for their own account (support transparency and account takeover detection). Failure detail may be summarized to reduce abuse assistance.

### 11.3 Login history retention

| Guidance | Specification |
| --- | --- |
| Policy | Login history retention follows operational policy |
| Purpose limitation | History is retained only as long as necessary for security, support, and compliance |
| Evolution | Retention periods may evolve |

---

## 12. Security Events

Security events must be recorded and aligned with audit logging requirements from roles/architecture/database docs.

| Event | Notes |
| --- | --- |
| Password changed | Authenticated change |
| Password reset | Recovery completed |
| Email changed | If/when supported |
| Login success | Include session/device context |
| Login failure | Throttled storage policy acceptable |
| Multiple failed logins | Threshold/alert signal |
| Session revoked | Self, password-driven, or admin |
| Admin forced logout | Privileged revoke |
| Premium granted | Cross-domain; still security-relevant |
| Role changed | Privileged identity change |

**Cross-reference:** Audit logging in [`03-user-roles.md`](03-user-roles.md) §10 and audit tables/projections in [`06-database-design.md`](06-database-design.md). This document does not alter those locked specs; it names the security-relevant event set session management must emit.

### 12.1 Security event severity (conceptual)

Severity is for **operational prioritization only**. No implementation is specified.

| Severity | Example events |
| --- | --- |
| **Critical** | Password reset; password change; email change; session revocation |
| **High** | Login from new device; admin session revocation |
| **Medium** | Multiple failed logins |
| **Low** | Successful logout |

---

## 13. Future Trusted Devices

**Future only — not V1 delivery scope.**

| Capability | Intent |
| --- | --- |
| Remember this device | Longer-lived trust marker after explicit consent |
| Trusted device expiration | Time-bound trust |
| Revoke trusted devices | User/admin revocation |

Trusted devices must not weaken the **3 active session** cap unless a future approved policy explicitly revises it.

### 13.1 Trusted device clarification

When introduced, trusted devices:

| Rule | Specification |
| --- | --- |
| Session cap | Do **not** bypass concurrent session limits |
| MFA | Do **not** bypass future MFA |
| Reviews | Do **not** bypass security reviews |
| Friction only | Only reduce future authentication friction if explicitly approved |

---

## 14. Future MFA

**Future only — not V1 delivery scope.**

| Method | Status |
| --- | --- |
| Email OTP | Future candidate |
| Authenticator app (TOTP) | Future candidate |
| Passkeys / WebAuthn | Future candidate |
| SMS OTP | **Excluded from V1** and not preferred as a primary future factor without separate approval |

MFA, when introduced, must integrate with session issuance and step-up for sensitive actions (password change, email change, premium purchase) via services—not template-only checks.

---

## 15. Security Headers

Conceptual production expectations (also reflected in architecture; restated here for security completeness):

| Control | Expectation |
| --- | --- |
| HTTPS | Required in production |
| HSTS | Enforce HTTPS continuity |
| CSP | Constrain script/style/resource origins for Templates + HTMX + Alpine |
| X-Frame-Options / frame ancestors | Mitigate clickjacking |
| X-Content-Type-Options | Reduce MIME sniffing risk |
| Referrer Policy | Limit sensitive referrer leakage |
| Secure Cookies | Secure flag on session cookies |
| HttpOnly | Session cookie not readable by JavaScript |
| SameSite | CSRF-resistant cookie posture appropriate to site design |

Headers complement—never replace—server-side authZ.

---

## 16. Account Recovery

| Step | Specification |
| --- | --- |
| Forgot password | User requests reset via email identifier |
| Email verification path | Reset delivered only to registered email channel |
| Recovery tokens | High-entropy; stored as non-reversible verifiers where applicable |
| Token expiration | Short-lived |
| One-time use | Token invalid after successful use or expiry |
| Post-reset | Force new password meeting policy; invalidate other sessions (§4) |

Recovery must be rate-limited (§7) and audited (§12).

---

## 17. Administrative Security

Aligned with [`03-user-roles.md`](03-user-roles.md) Super Admin boundaries.

### 17.1 Super Admin only

| Capability |
| --- |
| Force logout / emergency session revocation at broad policy scope |
| Security settings (including fourth-login behavior: reject vs terminate oldest) |
| Session policy configuration (timeouts within approved bounds, lockout thresholds) |

### 17.2 Admin

| Capability |
| --- |
| View a user’s sessions (support) |
| Revoke a user’s sessions (support) |
| Assist users with account lockout / recovery triage |

Admins must not redefine Super Admin–only security settings. All privileged session actions are audit-logged.

---

## 18. Privacy Considerations

| Topic | Policy stance |
| --- | --- |
| Minimal device tracking | Store only what is needed for session security, support, and user-visible device management |
| No password storage | Hashes only; never plaintext or reversible encryption for passwords |
| No sensitive browser fingerprinting | Avoid invasive cross-site fingerprinting techniques; prefer explicit session/device records |
| GDPR-friendly concepts | Purpose limitation, user visibility of sessions/login history, revocation controls |
| Bangladesh privacy considerations | Respect applicable local expectations for personal data handling, retention reasonableness, and support transparency |

Login history and device metadata are security/support data—not marketing profiles.

---

## 19. Mapping

| This document | Maps to |
| --- | --- |
| AuthN model, cookies, CSRF, HTTPS | [`04-system-architecture.md`](04-system-architecture.md) Authentication / Secure HTTP |
| Admin vs Super Admin session powers | [`03-user-roles.md`](03-user-roles.md) Administrative boundaries + audit |
| Future persistence of sessions/history | [`06-database-design.md`](06-database-design.md) (additive future alignment only; **do not edit locked `06` here**) |
| Fail closed / service-layer authZ | Architecture dependency rule + RBAC |

---

## 20. Email Verification

Conceptual requirements only; this section does not define implementation.

| Requirement | Specification |
| --- | --- |
| New registrations | Email verification is **required** for newly registered accounts |
| Token | Verification uses a secure, single-use, high-entropy, time-limited verification token |
| Resend | Verification emails may be resent with rate limiting |
| Sensitive actions | Premium purchase and other sensitive account actions may require a verified email |
| Operational recovery | Super Admin may manually verify accounts when necessary for operational recovery |
| Audit | Verification events must be audit-logged |

---

## 21. Security Notifications

Users should receive security notifications for important account events.

| Example event | Notes |
| --- | --- |
| New device login | V1 candidate |
| Password changed | V1 |
| Password reset completed | V1 |
| Email changed | When email change is supported |
| Sessions revoked | V1 |
| Login from new country | **Future** |
| Login from new browser | **Future** |

| Delivery | Specification |
| --- | --- |
| In-app notification | **V1** primary channel |
| Email | For critical events where appropriate |
| Secrets | Notifications must **not** expose secrets (tokens, passwords, full session identifiers) |

---

## 22. Logout Operations

Four distinct logout operations are recognized:

| Operation | Meaning |
| --- | --- |
| **Logout Current Device** | Ends only the session serving the current request/device |
| **Logout Selected Device** | Ends one chosen session/device from Device Management (not necessarily the current one) |
| **Logout All Other Devices** | Ends every active session except the current device session |
| **Logout All Devices** | Ends all active sessions for the account; the user must authenticate again on any device |

All logout operations are server-side session revocations and should produce security/audit events as applicable.

---

## 23. Credential Sharing Policy

| Rule | Specification |
| --- | --- |
| Individual use | Accounts are intended for **individual** use |
| Session cap | Maximum of **three** concurrent sessions under default policy |
| Excessive switching | Excessive device switching may trigger security review |
| Subscription abuse | Credential sharing intended to bypass subscription policy is **prohibited** |
| Enforcement | The platform may revoke sessions or suspend accounts after repeated abuse |
| Audit | Administrative enforcement actions must be audit-logged |

---

## 24. Security Log Retention

| Guidance | Specification |
| --- | --- |
| Retention | Security events should be retained according to operational policy |
| Audit form | Audit logs remain **append-only** |
| Evolution | Retention periods are platform policy and may evolve without changing the append-only nature of audit records |

---

## 25. Suspicious Login Detection (Future)

**Future only. No implementation required for Version 1.**

Possible signals (non-exhaustive):

- Login from unfamiliar country  
- Login from unfamiliar browser  
- Impossible travel  
- Excessive failed logins  
- Abnormal device switching  

---

## 26. Security Incident Response (Future)

**Future capability. Super Admin only.**

Possible emergency actions (conceptual):

- Platform-wide session revocation  
- Forced password reset  
- Temporary login suspension  
- Emergency maintenance mode  

---

## 26A. Email Change Security

Conceptual requirements only; this section does not define implementation.

| Requirement | Specification |
| --- | --- |
| Sensitivity | Changing the registered email is treated as a **security-sensitive** action |
| Confirmation | Current password confirmation is required |
| New email | The new email must be verified before becoming active |
| Prior email notice | The previous email address should receive a notification that an email change was requested or completed |
| Pending expiry | Pending email changes expire automatically after a configured period |
| Audit | Email change events are audit-logged |
| Sessions | Security policy may invalidate other active sessions after a successful email change |

---

## 26B. Sensitive Action Re-authentication

Certain high-risk actions may require the user to re-enter their password even when already authenticated.

| Example action |
| --- |
| Change password |
| Change email |
| View active device list |
| Logout all devices |
| Purchase Premium |
| Delete account (**Future**) |
| Other security-sensitive operations |

**Purpose:** Reduce risk from unattended authenticated sessions.

Conceptual only.

---

## 26C. Maintenance Login Policy (Future)

**Future only.**

| Concept | Specification |
| --- | --- |
| Capability | Super Admin may temporarily disable new logins during maintenance |
| Existing sessions | Existing administrative sessions may remain according to operational policy |

Future capability only.

---

## 26D. Future Single Sign-On (SSO)

**Future only.**

Reserved support candidates:

- Google  
- Microsoft  
- Apple  
- Institutional Identity Providers  

| Rule | Specification |
| --- | --- |
| Timing | Future capability only |
| Integration | Must integrate with existing RBAC, EntitlementService, and session lifecycle |
| Authorization model | Must **not** introduce a second authorization model |

---

## 27. Acceptance Criteria

This security specification is acceptable when:

1. Session security is fully specified for V1 web authentication  
2. Maximum concurrent active sessions is clearly defined as **3**  
3. Fourth-login behavior is defined as configurable (reject **or** terminate oldest)  
4. Device management fields and actions are defined  
5. Logical `UserSession` and Login History are defined without SQL/Django  
6. Password policy and login abuse controls are defined  
7. Session lifecycle and timeouts (idle **30 minutes**, absolute **30 days**) are defined  
8. Security events cross-reference audit expectations  
9. Trusted devices and MFA are explicitly **Future**-only; SMS excluded from V1  
10. **Email verification** is specified for new registrations and sensitive actions  
11. **Session refresh policy** distinguishes idle refresh from absolute lifetime  
12. **Security notifications** are specified (in-app V1; email for critical events)  
13. **Logout operations** distinguish current, selected, all-other, and all-devices  
14. **Credential sharing policy** is defined  
15. **Session fixation protection** and secure session identifier rules are defined  
16. **Security log retention** guidance is defined  
17. **Email change security** is specified  
18. **Sensitive action re-authentication** is specified  
19. **Session revocation propagation** is specified  
20. **Password strength guidance** is included  
21. **Session cookie / identifier rotation** is specified  
22. **CSRF clarification** covers HTMX and safe GET behavior  
23. **Rate limiting scope** may consider account, IP, device, and combined signals  
24. **Device naming guidance** and **country geolocation disclaimer** are defined  
25. **Security event severity** classification is defined  
26. **Trusted device clarification** states trust does not bypass session caps, MFA, or reviews  
27. **Device vs session terminology** is defined  
28. **Login history retention** guidance is defined  
29. **Future SSO** is reserved without a second authorization model  
30. Contains **no** implementation code, SQL, Django models, migrations, API endpoint specs, configuration examples, or UI implementation  
31. Does **not** modify locked documents `00`–`06`  

---

## 28. Document Lock

**Status:** `docs/07-security-and-session-management.md` is **Approved** and locked at **Version 1.0.0**.

Locked documents `docs/00`–`docs/06` remain unmodified. Next documentation proceeds only when explicitly requested.

---

*Nursilo — Learn. Practice. Succeed.*
