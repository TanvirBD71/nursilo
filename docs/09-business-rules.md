# Nursilo — Business Rules

| Field | Value |
| --- | --- |
| Document | `09-business-rules.md` |
| Version | `1.0.0` |
| Status | **Approved** — locked business rules specification |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`08`](08-api-design.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative business rule specification for the entire Nursilo platform |
| Out of scope | Django models; ORM; database schema; SQL; migrations; API endpoints; OpenAPI; UI implementation; source code |
| Nature | **Additive only** — does not modify locked docs `00`–`08` |

---

## 1. Purpose

This document defines **what** Nursilo must do—not **how** it is implemented.

Business rules exist separately from implementation so that:

- Product decisions remain stable across Templates, HTMX, future APIs, and Flutter  
- Services enforce one authoritative rule set  
- QA, support, and engineering share a single source of truth  
- Architecture, domain model, security, and API philosophy stay consistent in behavior  

Rules in this document are **deterministic**, **technology-independent**, **service-oriented**, and **auditable**. Where this document restates policy from approved docs `00`–`08`, it does so for operational completeness and does **not** amend those locked documents.

---

## 2. Business Rule Principles

| Principle | Rule |
| --- | --- |
| **Services own business rules** | Domain/application services are the sole enforcers of business decisions |
| **UI never enforces business logic** | Templates, HTMX, and clients may guide UX but must not be the authority |
| **Database complements, never replaces** | Constraints and indexes support integrity; they do not replace service rules |
| **Fail closed** | Missing identity, permission, entitlement, or invalid state → deny |
| **Deterministic behavior** | The same inputs and state produce the same allow/deny and outcomes |
| **Auditability** | Privileged and security-relevant decisions leave durable records |
| **Backward-compatible evolution** | Rule changes must preserve historical attempts, payments, and published history invariants |

---

## 3. User Account Rules

| Area | Business rules |
| --- | --- |
| **Registration** | Individuals may register one account per email; default role is Student; passwords must satisfy password policy |
| **Activation** | New accounts follow platform activation policy; email verification is required for newly registered accounts |
| **Email verification** | Unverified accounts are restricted from premium purchase and other sensitive actions that require verified email; verification uses single-use, time-limited tokens; resend is rate-limited; Super Admin may manually verify for operational recovery; verification is audited |
| **Profile updates** | Users may update basic profile and academic profile fields for their own account; email change is a sensitive action (password confirmation, verify new email before active, notify previous email, pending change expires, may invalidate other sessions, audited) |
| **Suspension** | Admin/Super Admin may suspend accounts for abuse or policy violations; suspended users cannot authenticate for normal learner/staff use |
| **Reactivation** | Privileged staff may reactivate suspended accounts per policy; action is audited |
| **Archival** | Accounts may be archived/deactivated operationally without destroying historical attempts or payment history |
| **Deletion policy** | Casual self-serve hard deletion of accounts with learning history is not a V1 learner right; any future deletion must preserve or lawfully handle attempt/payment/audit history per policy |

---

## 4. Authentication & Session Rules

Authoritative detail: [`07-security-and-session-management.md`](07-security-and-session-management.md). Summary rules:

| Area | Business rules |
| --- | --- |
| **Login** | Valid credentials required; failures are throttled/locked per policy; success creates a session within concurrent-session rules; session id regenerated after authentication |
| **Logout** | Distinct operations: current device, selected device, all other devices, all devices |
| **Concurrent sessions** | Default maximum **3** active sessions; 4th login rejects or terminates oldest (configurable); Super Admin may grant audited exceptions for QA/test/emergency accounts only |
| **Password reset** | Rate-limited; single-use tokens; on success, other sessions invalidated; may clear lockout |
| **Password change** | Requires authenticated context (and re-auth when policy requires); other sessions invalidated; identifiers rotated |
| **Session expiration** | Idle timeout **30 minutes**; absolute timeout **30 days**; activity refreshes idle only; absolute never extends via activity; expiry always requires re-authentication; UX warning ~5 minutes before idle expiry is non-authoritative |
| **Device management** | Users may view devices/sessions and revoke; auto-generated names; country from IP is approximate |
| **Sensitive re-auth** | Password change, email change, view devices, logout all, premium purchase, and similar actions may require password re-entry |
| **Credential sharing** | Accounts are individual-use; sharing to bypass subscription is prohibited; abuse may lead to session revoke or suspension |

---

## 5. RBAC Rules

Authoritative detail: [`03-user-roles.md`](03-user-roles.md). Summary rules:

| Area | Business rules |
| --- | --- |
| **Role permissions** | Access follows the approved matrices; deny by default |
| **Privilege escalation** | Users cannot self-assign higher privileges; Super Admin alone defines role permission sets and grants Super Admin |
| **Role assignment** | Admin may assign non–Super Admin roles per policy; all role changes are audited |
| **Approval authority** | Reviewers Approve; Authors do not Approve or Publish |
| **Publishing authority** | Editors/Admins/Super Admin Publish; Reviewers do not Publish by default |
| **Student isolation** | Students never access admin/authoring surfaces or unpublished learner discovery |

---

## 6. Subscription & Entitlement Rules

| Area | Business rules |
| --- | --- |
| **Free** | Core learning materials and limited practice; no complete bank, unlimited mocks, premium tracks, premium books/notes, or advanced analytics (except configured teasers) |
| **Premium** | Unlocks complete question bank, unlimited mocks, licensing/govt/NCLEX/Prometric tracks, premium books/notes, advanced analytics |
| **Expiration** | When Premium expires or is revoked, effective state returns to Free; premium capabilities deny immediately thereafter |
| **Renewal** | Successful verified payment extends/activates PremiumActive |
| **Manual grant** | Admin/Super Admin may grant/revoke Premium; must be audited; goes through billing/entitlement services |
| **Revocation** | Privileged revoke ends premium capabilities; audited |
| **Grace period** | If configured by Super Admin policy, a short grace may apply; default is fail closed when not PremiumActive |
| **Entitlement evaluation** | **EntitlementService alone** decides capability allow/deny for Free/Premium features; Assessment/Library never grant capabilities directly |
| **Pending payment** | Checkout may enter PendingPayment; capabilities do not activate until PaymentConfirmed or audited manual grant |

---

## 7. Learning Rules

| Area | Business rules |
| --- | --- |
| **Visibility** | Learners see only **Published** and non-archived content they are entitled to |
| **Publishing** | Content becomes learner-visible only via editorial Publish transitions |
| **Continue Learning** | Learners may resume from their last recorded learning position |
| **Progress** | Progress is tracked at lesson/topic granularity per learner |
| **Completion** | Completion marks are learner-owned progress facts; they do not issue certificates |
| **Archive** | Archived learning content leaves discovery; does not destroy related learner progress/history |

Staff may preview unpublished content per RBAC; Students may not.

---

## 8. Assessment Rules

| Area | Business rules |
| --- | --- |
| **Question lifecycle** | Draft → Review → Approved → Published → Archived |
| **Versioning** | Scored edits create a new question version (or equivalent); stable question identity remains |
| **Publishing** | Only published questions enter learner practice/exam pools |
| **Editing** | Editing published meaning must not rewrite historical attempts |
| **Archiving** | Soft delete/archive removes from pools; historical attempts remain reviewable |
| **Duplicate detection** | System should warn on likely duplicates; does not auto-merge identities |
| **Reuse** | One question identity may be linked to multiple topics and reused across practice/exams without duplicating source records |
| **Types / difficulty** | MCQ, True/False, Best Answer, Clinical Scenario, Image-Based; Easy/Medium/Hard/Expert |
| **Error reports** | Learners may report errors; staff triage/resolve per RBAC |

---

## 9. Practice Rules

| Area | Business rules |
| --- | --- |
| **Eligibility** | Authenticated Student; published entitled questions only |
| **Free limits** | Configurable free practice volume enforced; exceeding cap denies further free practice until reset/upgrade |
| **Premium limits** | Premium is not bound by free-tier caps |
| **Custom practice** | Filters (topic, difficulty, count, etc.) must resolve within inventory + entitlements |
| **Topic / chapter / subject practice** | Scope must match published hierarchy links |
| **Random practice** | Draws from entitled published pool |
| **Resume** | In-progress practice attempts may resume per attempt state rules where mode allows |

---

## 10. Exam Rules

| Area | Business rules |
| --- | --- |
| **Attempt creation** | Requires entitlement + published exam/set availability; respects session auth |
| **Submission** | User submit finalizes answers; no further mutation after Completed |
| **Timer** | Timed exams use server-authoritative remaining time |
| **Resume** | Only **InProgress** attempts; Completed cannot resume as live |
| **Auto submit** | On timeout, attempt submits automatically |
| **Retake** | Allowed only when exam definition/entitlement policy permits |
| **Completion** | Completed attempts are permanently stored (unless future retention policy applies) |
| **Scoring** | Uses frozen `QuestionVersion` references on attempt items—not latest head content |
| **Tracks** | Licensing, Government Job, NCLEX, Prometric sets are premium-gated |
| **Unlimited mocks** | Premium only |

---

## 11. Review Rules

| Area | Business rules |
| --- | --- |
| **Wrong answers** | Learners may review incorrect items from past attempts they own |
| **Bookmarks** | Learners may review bookmarked questions they own |
| **Attempt history** | Learners may view their own completed attempts and scores |
| **Explanations** | Shown when entitlement/policy allows |
| **Premium analytics** | Advanced analytics gated; basic progress may remain free |

Learners never access other users’ attempts, notes, or bookmarks.

---

## 12. Library Rules

| Area | Business rules |
| --- | --- |
| **Read** | Online reading requires Published + entitlement |
| **Download** | Downloads require entitlement and policy permission; never bypass freemium rules |
| **Visibility** | Unpublished/archived books hidden from learners |
| **Premium restrictions** | Premium-flagged books denied to Free users |
| **Archive behavior** | Archive removes from catalog discovery; does not rewrite history of entitled access events if retained |

---

## 13. CMS Rules

| Area | Business rules |
| --- | --- |
| **Draft** | Not public |
| **Review** | Staff review gate |
| **Approved** | Ready to publish; not yet public unless published |
| **Published** | Public/indexable per SEO rules |
| **Archived** | Removed from public discovery |
| **SEO** | Public published pages expose appropriate metadata; authenticated app areas non-indexed where appropriate |
| **Contact/feedback** | Submissions accepted; staff triage; no secrets in auto-replies |

---

## 14. Notification Rules

| Area | Business rules |
| --- | --- |
| **Announcements** | Staff-authored; only published announcements visible to targeted learners |
| **In-app notifications** | Primary V1 channel for security and system events |
| **Read state** | Recipients may mark read/unread for their own notifications |
| **Targeting** | Global or targeted per announcement policy |
| **Priority / severity** | Operational prioritization (e.g., security event severity) does not bypass delivery rules |
| **Delivery** | Critical security events may also email where appropriate; notifications never expose secrets |
| **Security notifications** | New device login, password/email changes, session revocation, etc. |

---

## 15. Search Rules

| Area | Business rules |
| --- | --- |
| **Published only** | Learners never receive unpublished catalog hits |
| **Entitlement-aware** | Results must not leak premium-only full payloads beyond allowed teasers |
| **Localization** | Bangla/English query competence per product maturity |
| **Ranking** | Deterministic enough for stable UX; not a second CMS |
| **Archive exclusion** | Archived entities excluded from learner search |

---

## 16. Analytics Rules

| Area | Business rules |
| --- | --- |
| **Weak / strong topics** | Derived from the learner’s own attempt data |
| **Progress** | Reflects learning + assessment activity owned by the learner |
| **Premium analytics** | Advanced views require Premium |
| **Admin analytics** | Content performance and question usage visible to permitted staff roles only |
| **Historical preservation** | Analytics must not mutate or erase attempt history; read models are rebuildable |

AI-ready signals may be retained; AI product features are not V1 rules that change scoring.

---

## 17. Payment Rules

| Area | Business rules |
| --- | --- |
| **Checkout** | Learner-initiated; Bangladesh-first gateways when enabled (bKash, Nagad, SSLCommerz) |
| **Verification** | Entitlements activate only after verified payment (or audited manual grant) |
| **Idempotency** | Duplicate confirmations must not double-grant incorrectly |
| **Failure** | Failed/unverified payments do not activate Premium |
| **Refund** | Privileged financial corrections follow admin policy and audit |
| **Manual grant** | Never a silent side effect of content publish; always explicit billing/entitlement path |
| **Audit** | Payment and subscription changes are mandatory audit events |

**Payments never directly grant permissions.** Only EntitlementService (after Billing confirmation) grants capabilities.

---

## 18. Audit Rules

| Area | Business rules |
| --- | --- |
| **Mandatory events** | Login success/failure (policy), role changes, content publication, question edits/versions, subscription changes, payment events, settings/security changes, session revokes, email verification/change, manual premium grants |
| **Append-only** | Audit records are not editable by Admin |
| **Visibility** | Super Admin full; Admin view (export limited); learners/authors no general audit access |
| **Retention** | Per operational policy; may evolve; append-only nature remains |

---

## 19. Error Rules

| Area | Business rules |
| --- | --- |
| **Validation** | Invalid input is rejected with clear, non-sensitive messages |
| **Authentication** | Unauthenticated or invalid session → deny |
| **Authorization** | Authenticated but forbidden → deny |
| **Business conflicts** | Illegal workflow, non-resumable attempt, free-tier cap, unpublished content → deny with domain-appropriate conflict |
| **Localization** | User-facing errors support Bangla and English |
| **Safety** | No stack traces, secrets, or unpublished-content leakage to Students |

---

## 20. Cross-Domain Rules

Non-negotiable truths spanning aggregates:

| # | Rule |
| --- | --- |
| 1 | Question edits never rewrite historical attempts |
| 2 | Archived content never destroys learner history |
| 3 | Payments never directly grant permissions |
| 4 | **EntitlementService alone** grants Free/Premium capabilities |
| 5 | **EditorialWorkflowService alone** publishes content (via allowed roles) |
| 6 | **Services alone** mutate aggregates; UI/API adapters do not |
| 7 | RBAC and entitlements are both required for privileged learner capabilities |
| 8 | Attempt items freeze question versions at attempt time |
| 9 | Search and analytics are projections—not sources of truth for scoring or entitlements |
| 10 | No certificate issuance exists in Nursilo |
| 11 | Soft delete/archive is the default destructive path for educational catalog content |
| 12 | Session validity is always server-side; browser state is never authoritative |

---

## 21. Future Business Rules

Reserved; **not** V1 enforcement scope:

| Area | Future rule posture |
| --- | --- |
| **Adaptive Learning** | May recommend practice from weak topics without altering historical attempts |
| **AI Tutor** | May explain using attempt context; must not mutate scored history |
| **Certificates** | Explicitly out of product goals; do not introduce |
| **Institution Licensing** | Post–product-market-fit tenancy; must not equal Super Admin |
| **Offline Mode** | Entitled offline subsets with sync conflict rules TBD; must not bypass entitlements |

---

## 22. Cross References

| Document | Consistency |
| --- | --- |
| [`03-user-roles.md`](03-user-roles.md) | RBAC matrices and Super Admin boundaries |
| [`04-system-architecture.md`](04-system-architecture.md) | Service ownership, events, transactions, dependency rule |
| [`05-domain-model.md`](05-domain-model.md) | Aggregates, invariants, ownership |
| [`06-database-design.md`](06-database-design.md) | Persistence complements rules; does not replace them |
| [`07-security-and-session-management.md`](07-security-and-session-management.md) | AuthN/session/device/password policies |
| [`08-api-design.md`](08-api-design.md) | API adapters enforce the same service rules |

This document does **not** modify those locked specifications.

---

## 23. Acceptance Criteria

This document is acceptable when:

1. All major business rule domains listed in §§3–21 are defined  
2. Rules are deterministic and fail closed  
3. Rules are implementation-independent (no code, schema, endpoints, UI)  
4. Rules align with approved documentation `00`–`08`  
5. Cross-domain invariants are explicit  
6. Future rules are clearly non-V1  
7. Locked documents `00`–`08` remain unmodified  

---

## 24. Document Lock

**Status:** `docs/09-business-rules.md` is **Approved** and locked at **Version 1.0.0**.

Locked documents `docs/00`–`docs/08` remain unmodified. Next documentation proceeds only when explicitly requested. No implementation artifacts will be generated until separately requested.

---

*Nursilo — Learn. Practice. Succeed.*
