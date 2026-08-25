# Nursilo — System Architecture


| Field              | Value                                                                                                                                                                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Document           | `04-system-architecture.md`                                                                                                                                                                                        |
| Version            | `1.0.0`                                                                                                                                                                                                            |
| Status             | **Approved** — locked system architecture                                                                                                                                                                          |
| Product            | Nursilo                                                                                                                                                                                                            |
| Depends on         | [`00-project-vision.md`](00-project-vision.md), [`01-system-requirements.md`](01-system-requirements.md), [`02-feature-list.md`](02-feature-list.md), [`03-user-roles.md`](03-user-roles.md) (all Approved v1.0.0) |
| Purpose            | Overall software architecture for Nursilo before domain model and database design                                                                                                                                  |
| Documentation note | Original sequence placed roadmap at `04`; order revised—architecture precedes roadmap and database design                                                                                                          |
| Next gated doc     | `05-domain-model.md`                                                                                                                                                                                               |


---

## 1. Purpose

This document defines the **software architecture** of Nursilo: a Bangladesh-first, freemium B2C **Nursing Learning Ecosystem**.

It establishes:

- How the system is decomposed into domains and Django applications
- Where business rules live (service layer), especially for the **Assessment System** core domain
- How authentication, authorization, entitlements, content lifecycle, and payments fit together
- How Version 1 (Django Templates + HTMX + Alpine.js) remains **API-first** and **AI-ready** for future Flutter and AI features

Out of scope for this document:

- Database schemas and ERDs
- Django model field definitions
- REST endpoint contracts
- Implementation code
- UI wireframes

---

## 2. Architectural Principles


| Principle                              | Architectural implication                                                                         |
| -------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Simplicity over unnecessary complexity | Prefer clear Django apps and explicit services; avoid premature microservices                     |
| Modular architecture                   | One bounded context ≈ one (or a small cluster of) Django app(s)                                   |
| Assessment System as core domain       | Question Bank, Practice, Exam, Review, and Analytics drive design priority                        |
| API-first                              | Domain services are the system of record for rules; Templates and future DRF/Flutter are adapters |
| Clean Architecture where practical     | Presentation → Application/Services → Domain rules → Persistence abstractions                     |
| SOLID where appropriate                | Especially entitlement checks, exam attempt lifecycle, and content publishing                     |
| Django best practices                  | Explicit apps, settings split by environment, migrations discipline, ORM-first persistence        |
| Security by design                     | AuthN/AuthZ/entitlements enforced server-side; fail closed                                        |
| Performance by design                  | Query discipline, pagination, conceptual caching at read-heavy edges                              |
| Reusable composable content            | Shared content objects linked many-to-many; no siloed duplicates                                  |
| Multilingual without table duplication | Translation/locale strategy at content layer (detailed in database design doc)                    |
| Soft delete / archival default         | Important content is archived, not hard-deleted                                                   |
| Attempt integrity                      | Question edits must not rewrite historical attempts (versioning or equivalent)                    |
| AI-ready                               | Preserve structured attempt and content signals for future tutor/adaptive features                |
| Production-ready from day one          | Logging, error handling, secrets, Cloudflare + cPanel Passenger posture                           |


---

## 3. High-Level System Architecture

```text
                    ┌──────────────────────────────────────┐
                    │     Clients (V1)                     │
                    │  Browser: Templates + HTMX + Alpine  │
                    │  (Future: Flutter via API adapter)   │
                    └──────────────────┬───────────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │     Presentation Adapters            │
                    │  Django Views / Template responses   │
                    │  (Future: DRF API adapters)          │
                    └──────────────────┬───────────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │     Application / Service Layer      │
                    │  Use-cases: start exam, publish,     │
                    │  grant entitlement, search, etc.     │
                    └──────────────────┬───────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
┌─────────▼─────────┐      ┌───────────▼──────────┐      ┌──────────▼─────────┐
│ Domain Policies   │      │ Cross-cutting        │      │ Integration Ports  │
│ RBAC, Entitlements│      │ Logging, auditing,   │      │ Payments, email,   │
│ Publishing rules  │      │ i18n, validation     │      │ Cloudflare edge    │
└─────────┬─────────┘      └───────────┬──────────┘      └──────────┬─────────┘
          │                            │                            │
          └────────────────────────────┼────────────────────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │ Persistence (conceptual repositories)│
                    │ PostgreSQL + media/object storage    │
                    └──────────────────────────────────────┘
```

**V1 runtime shape:** modular monolith on Django, deployed via cPanel Passenger, fronted by Cloudflare, data in PostgreSQL.

---

## 4. Core Domains


| Domain                     | Responsibility                                                         | Priority      |
| -------------------------- | ---------------------------------------------------------------------- | ------------- |
| **Identity & Access**      | Accounts, sessions, roles, RBAC                                        | Foundation    |
| **Entitlements & Billing** | Free/Premium rights, subscriptions, payments                           | Foundation    |
| **Learning**               | Course hierarchy, lessons, learning materials, progress                | Supporting    |
| **Assessment (core)**      | Question Bank, Practice, Exam, Review, attempt integrity               | **Core**      |
| **Analytics**              | Weak/strong topics, progress, admin content/question stats             | Core-adjacent |
| **Library**                | Multi-format books/resources, read/download entitlements               | Supporting    |
| **Discovery**              | Global search                                                          | Supporting    |
| **Engagement**             | Notifications, announcements, notes, bookmarks, goals, streaks         | Supporting    |
| **Publishing / CMS**       | Blog, pages, SEO, contact/feedback, editorial workflow shared patterns | Supporting    |
| **Platform Ops**           | Settings, feature toggles, audit logs, admin reporting                 | Foundation    |


Learning exists primarily to **feed and contextualize** Assessment—not as a certificate LMS.

---

## 5. Bounded Contexts


| Bounded context      | Owns                                                                  | Must not own                                                                        |
| -------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Identity             | User account, credentials, profile, academic profile, role assignment | Exam scoring rules                                                                  |
| Access Control       | Permission checks, role matrices                                      | Payment merchant secrets usage details (config owned by Platform Ops / Super Admin) |
| Entitlements         | Whether a principal may use a capability now                          | Question content authoring                                                          |
| Learning Catalog     | Hierarchy nodes, materials, progress pointers                         | Attempt answer keys                                                                 |
| Assessment Catalog   | Questions, versions, blueprints, pools                                | Subscription invoices                                                               |
| Assessment Runtime   | Attempts, timers, resume state, scoring outcomes                      | CMS pages                                                                           |
| Library              | Book metadata, formats, reading entitlements application              | Role definitions                                                                    |
| Search               | Indexing/query orchestration across published entitled projections    | Authoring workflow transitions                                                      |
| Analytics            | Aggregations and derived learner/admin insights                       | Mutating exam answers                                                               |
| Notifications        | Delivery of in-app (and later email) messages                         | Content approval                                                                    |
| CMS / Communications | Public pages, blog, announcements, contact inbox                      | Question bank truth                                                                 |
| Platform             | Settings, toggles, audit store, backup posture                        | Pedagogical content                                                                 |


**Anti-corruption rule:** Presentation adapters never bypass Entitlements or Access Control when entering Assessment Runtime.

---

## 6. Django Application Boundaries

Recommended V1 app map (logical boundaries; names may be refined at implementation without changing meaning):


| App (logical)                           | Bounded context                                           |
| --------------------------------------- | --------------------------------------------------------- |
| `accounts`                              | Identity, academic profile, language preference           |
| `rbac` or permissions within `accounts` | Role checks helpers (keep thin; matrix from `03`)         |
| `entitlements`                          | Free/Premium capability evaluation                        |
| `billing`                               | Subscriptions, payment orchestration                      |
| `learning`                              | Hierarchy, materials, progress, continue-learning         |
| `assessment`                            | Question bank, practice, exams, review, attempt integrity |
| `analytics`                             | Learner and admin analytical read models                  |
| `library`                               | Books and resources                                       |
| `search`                                | Global search façade                                      |
| `engagement`                            | Notes, bookmarks, goals, streaks                          |
| `notifications`                         | In-app notifications, announcements                       |
| `cms`                                   | Blog, pages, SEO fields, contact/feedback                 |
| `audit`                                 | Audit event recording and admin retrieval                 |
| `platform`                              | Settings, feature toggles                                 |
| `api` (optional package)                | Future/versioned DRF adapters calling the same services   |


**Rules**

- Apps may **call services** of other apps; they must not reach into another app’s private persistence helpers casually.
- Circular imports between domain services are a design smell—introduce shared kernels only for truly cross-cutting types (e.g., entitlement codes, audit event types).

---

## 7. Domain Services & Service Layer

### 7.1 Service layer responsibility

The **service layer** is the home of use-cases:

- Start practice / start exam / resume exam / submit attempt
- Publish content / archive content / preview authorization
- Evaluate entitlement for a capability
- Grant premium after verified payment
- Record audit events for privileged actions

Views/templates (and future API views) should:

1. Authenticate identity
2. Parse input
3. Call a service
4. Render/return the result

They should **not** embed scoring, publishing, or entitlement rules.

### 7.2 Domain services (conceptual catalog)


| Service                    | Primary behaviors                                                  |
| -------------------------- | ------------------------------------------------------------------ |
| `AccountService`           | Register, profile update, academic profile                         |
| `AccessControlService`     | Permission checks against RBAC matrix                              |
| `EntitlementService`       | Capability allow/deny for Free/Premium                             |
| `LearningCatalogService`   | Navigate hierarchy, compose M2M links                              |
| `ProgressService`          | Continue learning, lesson/topic progress                           |
| `EditorialWorkflowService` | Draft → Review → Approved → Published → Archived transitions       |
| `QuestionBankService`      | Create/edit/version questions, duplicate hints                     |
| `PracticeService`          | Build sessions from scopes/filters; enforce free caps              |
| `ExamService`              | Timed exams, mocks, resume, submit, persist attempts               |
| `ReviewService`            | Wrong-answer and bookmark review projections                       |
| `AnalyticsService`         | Weak/strong topics, advanced analytics gating                      |
| `LibraryService`           | Catalog, read, download permission                                 |
| `SearchService`            | Entitlement-aware multi-type search                                |
| `NotificationService`      | In-app notifications, announcements                                |
| `BillingService`           | Checkout initiation, webhook verification, entitlement activation  |
| `AuditService`             | Append-only privileged event records                               |
| `SettingsService`          | Feature toggles, freemium caps (respecting Super Admin boundaries) |


---

## 8. Repository Responsibilities (Conceptual)

Repositories (or equivalent persistence gateways) abstract storage so services stay testable and API-first.


| Repository concern       | Responsibility                                                | Must not                                |
| ------------------------ | ------------------------------------------------------------- | --------------------------------------- |
| Content repositories     | Load/save catalog entities, soft-delete flags, workflow state | Enforce freemium rules alone            |
| Attempt repositories     | Persist immutable attempt snapshots / version references      | Mutate historical answer keys silently  |
| Entitlement repositories | Store subscription state                                      | Decide pedagogical correctness          |
| Audit repositories       | Append audit events                                           | Allow update/delete of history by Admin |
| Search index gateway     | Update/query search projections                               | Be the source of truth for content      |


**Unit of work:** one user-facing action (e.g., submit exam) should commit consistently across attempt persistence, analytics signals, and audit where required.

---

## 9. Authentication Architecture


| Concern        | V1 approach                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------- |
| Primary auth   | Server-side session authentication for web                                                                          |
| Identity store | Django-managed user identity in PostgreSQL                                                                          |
| Credentials    | Strong password hashing; secrets outside source control                                                             |
| Recovery       | Password reset via secure, time-limited token flow                                                                  |
| Session        | HTTP-only secure cookies behind HTTPS (Cloudflare → origin)                                                         |
| Future mobile  | Token-based auth adapter (e.g., DRF token/JWT strategy decided later) calling the same Account/Entitlement services |
| Audit          | Login success/failure and password reset completion logged per RBAC audit requirements                              |


Academic profile is part of Identity context but consumed later by Analytics/personalization—**not** a separate auth factor.

---

## 10. Authorization Architecture

Authorization is **two-layered**:

```text
Request
  → Authentication (who is the principal?)
  → RBAC (what role permissions exist?)     [03-user-roles.md]
  → Entitlement (what plan capabilities?)  [Free/Premium]
  → Domain policy (workflow state, publish state, ownership)
  → Allow / Deny (fail closed)
```


| Layer         | Answers                                                                   |
| ------------- | ------------------------------------------------------------------------- |
| RBAC          | May this Editor publish? May this Student open admin?                     |
| Entitlement   | May this Student start unlimited mocks?                                   |
| Domain policy | Is this question Published? Is this attempt still in progress for resume? |


**Presentation must not be the enforcer.** HTMX endpoints and future API routes share the same AccessControl + Entitlement services.

Preview of unpublished content is an RBAC-allowed staff path, never a Student path.

---

## 11. Assessment System Architecture (Core)

```text
Question Bank (versioned catalog)
        │
        ▼
 Practice Builder / Exam Blueprint
        │
        ▼
 Assessment Runtime (attempt lifecycle)
        │
        ├── Timer / Resume state
        ├── Answer capture
        ├── Scoring
        └── Immutable attempt record (+ question version reference)
                │
                ├── Review projections
                └── Analytics signals
```

### Key architectural decisions


| Decision                                   | Rationale                                                   |
| ------------------------------------------ | ----------------------------------------------------------- |
| Catalog vs Runtime split                   | Authoring changes must not corrupt live/historical attempts |
| Question versioning or snapshot-on-attempt | Satisfies historical integrity requirement                  |
| Entitlement checks at start and submit     | Prevents URL/API bypass                                     |
| Soft delete in catalog                     | Removed from pools; historical attempts remain reviewable   |
| M2M topic links                            | Academically valid multi-topic questions                    |
| Resume interrupted exam                    | Server-authoritative remaining time and saved answers       |


Practice is formative runtime; Exam/Mock is structured runtime—**shared attempt engine**, different policies (timing, caps, blueprints).

---

## 12. Learning System Architecture

```text
Course → Subject → Unit → Chapter → Topic → Lesson → Learning Material
                         │
                         ├── M2M links to Assessment catalog
                         └── Progress / Continue Learning pointers
```


| Concern       | Architecture                                             |
| ------------- | -------------------------------------------------------- |
| Hierarchy     | Ordered composition with reusable nodes                  |
| Composability | Same material/question linked into multiple contexts     |
| Visibility    | Only Published nodes in learner navigation               |
| Progress      | Per-learner pointers at lesson/topic granularity         |
| Editorial     | Shared EditorialWorkflowService with other content types |
| Soft delete   | Archived nodes excluded from discovery                   |


Learning services **announce context** to Assessment (e.g., practice by topic); they do not score attempts.

---

## 13. Book Library Architecture


| Concern      | Architecture                                                                    |
| ------------ | ------------------------------------------------------------------------------- |
| Catalog      | Metadata + multi-course M2M + format descriptors (PDF, EPUB, HTML, image-based) |
| Delivery     | Online reader path; optional download path                                      |
| Entitlements | LibraryService asks EntitlementService before read/download                     |
| Lifecycle    | Same editorial + soft-delete patterns as learning content                       |
| Search       | Published entitled projections included in global search                        |


Downloads are never a side door around entitlements.

---

## 14. Search Architecture


| Concern         | Architecture                                                                      |
| --------------- | --------------------------------------------------------------------------------- |
| Scope           | Courses, books, lessons, questions, authors                                       |
| Source of truth | Domain catalogs; search is a projection                                           |
| Security        | Filter by publish state + entitlement; teaser-only for forbidden premium payloads |
| Locale          | Bangla/English query competence (V1 basic → improve in V1.1)                      |
| Updates         | Reproject on publish/archive/restore events                                       |


Search must not become a second CMS.

---

## 15. Analytics Architecture


| Layer               | Role                                                                             |
| ------------------- | -------------------------------------------------------------------------------- |
| Event/signal intake | Attempt results, progress updates, reading signals (as available)                |
| Derivation          | Weak/strong topics, accuracy, usage counts                                       |
| Learner views       | Basic free vs advanced premium (EntitlementService)                              |
| Admin views         | Content performance, question usage statistics                                   |
| AI-ready store      | Retain attempt-level structure (topic, correctness, timing, question version id) |


Analytics is primarily **read-model** oriented. It must not mutate Assessment Runtime history.

---

## 16. Notification Architecture


| Channel              | V1                                           | Later                  |
| -------------------- | -------------------------------------------- | ---------------------- |
| In-app notifications | Primary                                      | Continue               |
| Announcements        | Admin-published targeted/global messages     | Expand targeting       |
| Email                | Password reset / key billing (V1.1 emphasis) | Broader lifecycle mail |


NotificationService is a delivery boundary. Domain services emit notification intents after state changes (publish announcement, payment confirmed)—they do not render UI.

---

## 17. Payment Architecture

```text
Student checkout
    → BillingService starts payment with gateway port (bKash / Nagad / SSLCommerz)
    → Gateway
    → Verified callback/webhook
    → BillingService (idempotent) activates entitlement
    → AuditService records payment + subscription change
```


| Rule                                   | Meaning                                                           |
| -------------------------------------- | ----------------------------------------------------------------- |
| Verification required                  | No premium without verified payment (except audited manual grant) |
| Idempotency                            | Duplicate webhooks do not corrupt subscription state              |
| Super Admin configures gateways        | Per RBAC boundaries                                               |
| EntitlementService reads billing state | Assessment/Library never talk to gateways directly                |


Manual premium grant is an Admin/Super Admin path through BillingService + AuditService.

---

## 18. Content Lifecycle Architecture

Shared state machine across learning objects, questions, books, and CMS where applicable:

```text
Draft → Review → Approved → Published → Archived
         ↑______ reject ____|
Archived → Restore → (policy-defined re-entry state)
```


| Component                | Role                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------ |
| EditorialWorkflowService | Validates transition + actor permission                                                    |
| Preview                  | Staff-only rendering path for non-published states                                         |
| Publish event            | Triggers search reproject, learner visibility, audit                                       |
| Archive                  | Soft delete semantics for discovery                                                        |
| Bulk import              | Enters as Draft (or explicit staff-controlled state), never silent Public without workflow |


---

## 19. AI-Ready Architecture

V1 ships **no AI product features**, but architecture preserves:


| AI-ready element                                      | Why                                                                                           |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Structured attempts with topic + correctness + timing | Adaptive practice later                                                                       |
| Question version identity on attempts                 | Safe tutoring on what the learner actually saw                                                |
| Weak/strong topic projections                         | Recommendation inputs                                                                         |
| Service boundaries                                    | Future AI tutor as a new adapter/service calling Assessment/Analytics—not rewriting Templates |
| Content graph composability                           | Grounding explanations in linked lesson/material context                                      |


AI services must remain **read-mostly** relative to historical attempts.

---

## 20. API-First Architecture

```text
                    ┌─────────────┐     ┌──────────────┐
                    │ Template UI │     │ Future DRF   │
                    │ HTMX/Alpine │     │ Flutter apps │
                    └──────┬──────┘     └──────┬───────┘
                           │                   │
                           └─────────┬─────────┘
                                     ▼
                            Service Layer (shared)
```


| V1                                       | Future                                                              |
| ---------------------------------------- | ------------------------------------------------------------------- |
| Django Templates as the first adapter    | Versioned HTTP API adapter                                          |
| Same Entitlement/Exam/Editorial services | Mobile uses tokens; same services                                   |
| No business rules only in templates      | Contract doc comes later (`10-api-design` or renumbered equivalent) |


---

## 21. Deployment Architecture

```text
Users → Cloudflare (DNS, TLS, CDN, WAF posture)
                 → Origin (cPanel Passenger + Django)
                          → PostgreSQL
                          → Media/file storage on host or attached storage
```


| Element      | V1 posture                                                 |
| ------------ | ---------------------------------------------------------- |
| App server   | Passenger serving modular Django monolith                  |
| Data         | Managed/hosted PostgreSQL                                  |
| Edge         | Cloudflare in front of origin                              |
| Secrets      | Environment-based; never in git                            |
| Environments | Local / staging (if available) / production settings split |


Redis/Celery/R2 remain **future scale-out**, not V1 requirements.

---

## 22. Scalability Strategy


| Phase  | Strategy                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------- |
| V1     | Vertical scaling of monolith; efficient queries; pagination; Passenger process tuning               |
| Growth | Read replicas / stronger DB tier; CDN for static; Cloudflare caching for public CMS                 |
| Later  | Async workers (Celery), Redis cache, object storage (R2) for media, API horizontal scale for mobile |


Design services to be **stateless per request** (session/attempt state in DB), enabling future horizontal web workers without rewriting domains.

---

## 23. Caching Strategy (Conceptual Only)


| Cache candidate            | Approach                                                                                      |
| -------------------------- | --------------------------------------------------------------------------------------------- |
| Public CMS pages           | Edge/CDN caching with purge on publish                                                        |
| Published catalog listings | Application-level cache with invalidate-on-publish/archive                                    |
| Entitlement checks         | Short-lived cache optional; must invalidate on grant/revoke/payment                           |
| Search                     | Depends on search backend; keep consistency with publish events                               |
| Attempt runtime            | Prefer authoritative DB state for timers/resume—do not cache “remaining time” only in browser |


**Rule:** Never cache authorization decisions longer than entitlement/RBAC change propagation allows.

---

## 24. File Storage Strategy


| Asset type                                             | Strategy                                                                                                |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| Book files (PDF/EPUB), learning media, question images | Stored via Django media/storage backend on V1 hosting                                                   |
| Access                                                 | Always mediated by Library/Assessment services + entitlements (signed/controlled delivery conceptually) |
| Soft delete                                            | Unlink from catalog first; physical cleanup can be deferred/policy-based                                |
| Future                                                 | Migrate large blobs to Cloudflare R2 without changing service interfaces (storage port)                 |


---

## 25. Logging Strategy


| Log class           | Use                                                              |
| ------------------- | ---------------------------------------------------------------- |
| Application errors  | Exception stack traces to server logs for ops                    |
| Request diagnostics | Correlation-friendly request logs (no secrets/PII sprawl)        |
| Audit events        | Durable business audit trail via AuditService (see RBAC §10)     |
| Payment logs        | Gateway correlation ids + verification outcomes (no raw secrets) |


Separate **ops logs** (ephemeral/rotating) from **audit logs** (retained, admin-visible, non-editable).

---

## 26. Error Handling Strategy


| Layer           | Behavior                                                                                           |
| --------------- | -------------------------------------------------------------------------------------------------- |
| Domain/services | Raise typed domain errors (not allowed, not found, conflict, entitlement denied, workflow illegal) |
| Presentation    | Map to user-safe messages; HTMX partials return appropriate status                                 |
| Payments        | Fail closed on unverified callbacks; safe user messaging                                           |
| Exams           | Timer expiry and resume conflicts resolved server-side with deterministic rules                    |
| Security        | Do not leak existence of protected unpublished content to Students                                 |


User-facing errors must be localized (Bangla/English) at the presentation edge.

---

## 27. Future Mobile Architecture

```text
Flutter App → Versioned HTTPS API adapter → Shared service layer → PostgreSQL
```


| Concern     | Direction                                                     |
| ----------- | ------------------------------------------------------------- |
| Auth        | Token-based mobile auth adapter                               |
| Parity      | Practice, exam, resume, review, entitlements match web rules  |
| Offline/PWA | Future; sync through attempt services with conflict rules TBD |
| Push        | Future notification channel beside in-app                     |


Mobile must not embed a second entitlement implementation.

---

## 28. Cross-Cutting Concern Map


| Concern       | Owning mechanism                            |
| ------------- | ------------------------------------------- |
| i18n UI       | Identity preference + presentation catalogs |
| i18n content  | Content translation strategy (DB doc)       |
| RBAC          | AccessControlService + `03-user-roles.md`   |
| Freemium      | EntitlementService                          |
| Audit         | AuditService                                |
| Soft delete   | Persistence convention + catalog services   |
| Observability | Logging + audit + admin reports             |


---

## 29. Domain Events

Domain events are **conceptual signals** that a meaningful business state change occurred. They are not a Version 1 message-bus product requirement.

| Event class (conceptual) | Emitted when | Typical consumers (conceptual) |
| ------------------------ | ------------ | ------------------------------ |
| Content lifecycle | Draft / Review / Approve / Publish / Archive / Restore | Search projection, CDN purge intent, audit, notifications |
| Assessment attempt | Practice/exam started, resumed, submitted, expired | Analytics signals, review availability, entitlement usage |
| Entitlement / billing | Payment verified, premium granted/revoked, subscription changed | Access decisions, audit, learner notifications |
| Identity / RBAC | Login, role change, privileged admin action | Audit trail |
| Catalog / library | Book or material visibility change | Search projection, mediated media access checks |

**Rules:**

- Domain services own when an event is conceptually raised; presentation adapters do not invent business events.
- Version 1 may apply side effects **in-process** after a successful unit of work (same request) without an external broker.
- Future workers (Celery/Redis) may subscribe to the same conceptual events without rewriting domain boundaries.
- Events must never become a second source of truth for catalogs, attempts, or entitlements.
- Audit-worthy outcomes remain durable via AuditService even when delivery of notifications is best-effort.

---

## 30. Transaction Strategy

Business-critical changes must complete as coherent units of work so partial updates cannot leave learners or billing in an inconsistent state.

| Unit of work | Atomicity expectation |
| ------------ | --------------------- |
| Verified payment + entitlement activation | Succeed together or leave no premium grant from an unverified/partial path |
| Exam/practice submit (answers + score outcome + attempt terminal state) | Single coherent commit; resume/submit conflicts resolve server-side |
| Role change + audit record | Permission change is not silent; audit accompanies the change |
| Publish/archive + projection invalidation intent | Catalog state is authoritative; search/CDN follow as projections |
| Manual premium grant/revoke | Billing/entitlement path + audit; never a silent DB tweak |

**Rules:**

- Prefer one transactional boundary per use case at the service layer.
- Cross-boundary side effects that cannot share a DB transaction (email, CDN purge, search reindex) run **after** the authoritative commit, with clear retry/idempotency expectations.
- Payment webhooks remain **idempotent**: duplicate confirmed events must not double-extend incorrectly.
- Attempt integrity and entitlement checks are evaluated inside the service transaction, not only in the UI.
- Soft-delete and restore follow the same transactional discipline as publish paths.

---

## 31. Background Job Strategy

| Phase | Posture |
| ----- | ------- |
| Version 1 | Prefer synchronous, in-request work on the modular monolith (Passenger) for correctness-critical paths |
| Acceptable deferred work (V1) | Non-critical projection refresh, physical media cleanup, and similar policy-based maintenance when they do not block the learner's authoritative result |
| Growth / later | Introduce async workers (e.g., Celery) and Redis-backed queues without moving business rules out of domain services |

**Rules:**

- Background jobs are **adapters** that call the same services; they do not own entitlement, scoring, or publish rules.
- Jobs that mutate entitlements, attempt state, or roles must be idempotent and audited like interactive admin actions.
- Timer expiry and exam integrity remain server-authoritative; a job may assist enforcement but must not invent a second clock rule in the client.
- Failure of a non-critical job must not silently roll back a completed payment or submitted attempt; compensate or retry instead.
- Redis/Celery remain explicit seams from the scalability strategy—not Version 1 blockers.

---

## 32. Configuration Architecture

| Configuration class | Ownership | Notes |
| ------------------- | --------- | ----- |
| Secrets (DB, gateway keys, signing material) | Environment / host secret store | Never committed to git; rotated operationally |
| Deploy/runtime settings | Environment-specific settings modules | Local / staging / production split |
| Feature toggles & operational settings | Platform Ops domain | Admin/Super Admin per RBAC; audited when privileged |
| Payment gateway enablement | Super Admin via Billing configuration path | Fail closed when misconfigured |
| Edge/CDN behavior | Cloudflare + publish purge discipline | Complements, does not replace, app authorization |

**Rules:**

- Domain services read configuration through a narrow platform/settings boundary—not scattered magic values in templates.
- Changing a toggle must not bypass RBAC or entitlement enforcement.
- Public marketing/CMS caching configuration is separate from attempt-runtime authority (attempts stay DB-authoritative).
- AI, mobile token modes, and object-storage backends are future configuration seams behind existing ports.

---

## 33. Security Headers

Security headers and edge posture reduce common web risks; they complement—not replace—service-layer authorization.

| Layer | Responsibility |
| ----- | -------------- |
| Cloudflare edge | TLS termination posture, WAF/CDN controls in front of origin |
| Application (Django) | Standard secure response headers and cookie security flags appropriate to the deploy |
| Session / CSRF | Browser session hardening for Templates + HTMX; APIs later use their own token adapter rules |
| Content disposition | Controlled delivery for privileged media; avoid open passthrough of entitled files |

**Rules:**

- Headers never substitute for RBAC, entitlement, or publish-state checks.
- Admin and learner cookies must not expose secrets or raw payment credentials.
- Error responses remain user-safe and localized at the presentation edge without leaking stack traces or existence of unpublished content to Students.
- Future API/mobile clients inherit the same authorization model; header strategy may differ by adapter.

---

## 34. Media Access Architecture

Learning media, book files, and question assets are **not** public static shortcuts by default.

| Concern | Architecture |
| ------- | ------------ |
| Storage | V1 media/storage backend on host (future R2 behind the same storage port) |
| Authorization | Library/Assessment (or owning catalog service) + EntitlementService + publish/visibility rules |
| Delivery | Mediated/controlled delivery conceptually (signed or gated access)—not raw unprotected URLs for premium assets |
| Soft delete | Unlink from catalog first; physical cleanup may be deferred by policy |
| Audit | Privileged bulk access or grant paths that affect media availability are auditable |

**Rules:**

- Presentation layers request media through services; templates do not embed a parallel entitlement implementation.
- Teaser/free samples remain explicitly modeled; absence of entitlement must not leak full premium payloads via search or direct links.
- Historical assessment attempts must keep enough asset identity for review even if catalog media is later archived (attempt integrity over live catalog mutability).
- Migrating blobs to object storage must not require rewriting domain entitlement rules.

---

## 35. Search Projection Pipeline

Search is a **projection** of published, entitled catalog truth—not a second CMS.

| Stage | Meaning |
| ----- | ------- |
| Source commit | Authoritative publish/archive/restore (or equivalent visibility change) in domain catalogs |
| Invalidate / enqueue | Conceptual projection update intent after the source commit |
| Reproject | Update search documents for courses, books, lessons, questions, authors in scope |
| Query | Apply publish-state and entitlement filters; teaser-only where premium payloads are forbidden |
| Locale | Bangla/English query competence (V1 basic; improve later) |

**Rules:**

- Editors never "publish by indexing"; indexing follows catalog state.
- Projection lag is eventually consistent; learners' entitlement denials remain enforced at service boundaries even if an index is stale.
- Rebuild/reindex maintenance jobs use the same projection rules as incremental updates.
- Search adapters may change backend technology without changing Assessment or Learning domain ownership.

---

## 36. State Machines

Critical lifecycles are explicit state machines enforced in domain services.

| Machine | States (conceptual) | Enforcement notes |
| ------- | ------------------- | ----------------- |
| Editorial content | Draft → Review → Approved → Published → Archived (+ restore paths as defined) | Role-gated transitions; Students consume Published only |
| Question bank items | Same editorial pattern with attempt-integrity constraints | Edits must not rewrite historical attempts (versioning or equivalent) |
| Practice attempt | Started → In progress → Submitted / Abandoned (as defined) | Entitlement checked at start and submit |
| Exam attempt | Started → In progress → Resumable (policy) → Submitted / Timed out | Server timer and resume conflict rules are authoritative |
| Subscription / entitlement | Inactive → Active premium → Expired / Revoked (+ manual grant) | Only Billing/Entitlement paths mutate; idempotent against webhooks |
| Payment intent | Initiated → Pending verification → Confirmed / Failed | No premium without verification (except audited manual grant) |

**Rules:**

- Illegal transitions raise domain errors; UI cannot force them.
- Each transition that is privileged or financially material emits audit and, where appropriate, notification intents.
- State storage details belong in later domain-model/database documents; this architecture only fixes ownership and enforcement locus.

---

## 37. Dependency Rule

Dependencies point **inward** toward domain rules; adapters depend on services, never the reverse.

| From | May depend on | Must not depend on |
| ---- | ------------- | ------------------ |
| Templates / HTMX / Alpine (presentation) | Application/service facades | Persistence details, gateway SDKs, direct SQL for rules |
| Future DRF / Flutter adapters | Same application/service layer | A second copy of entitlement or scoring logic |
| Domain services | Domain policies, repository ports, sibling services via stable facades | Circular service graphs; presentation concerns |
| Infrastructure adapters (DB, storage, payment gateway, mail, search engine) | Interfaces defined by application/domain needs | Ownership of business invariants |
| Cross-cutting (Audit, AccessControl, Entitlement) | Shared kernels only where truly cross-cutting | Becoming a dumping ground for unrelated catalog logic |

**Rules:**

- Assessment remains the core domain; Learning, Library, CMS, and Billing support it without inverting priority.
- Circular imports between domain services are a design smell—introduce shared kernels only for shared codes/types (entitlement codes, audit event types).
- New features land in the owning bounded context/Django app; convenience shortcuts across apps do not bypass AccessControlService or EntitlementService.

---

## 38. Architecture Acceptance Criteria

This architecture is acceptable when it:

1. Centers the Assessment System as the core domain
2. Keeps business rules in a shared service layer (API-first)
3. Separates catalog authoring from attempt runtime integrity
4. Enforces RBAC + entitlements + workflow as layered authorization
5. Defines clear Django app / bounded context boundaries
6. Remains deployable as a Version 1 modular monolith on cPanel Passenger + Cloudflare + PostgreSQL
7. Leaves explicit seams for AI, mobile, Redis/Celery/R2 without mandating them in Version 1
8. Clarifies domain events, transactions, background work, configuration, security headers, media access, search projection, state machines, and dependency direction
9. Avoids database schemas, model definitions, API contracts, and code

---

## 39. Document Lock

**Status:** `docs/04-system-architecture.md` is **Approved** and locked at **Version 1.0.0**.

This document is the definitive system architecture for Nursilo Version 1. Next gated document is `docs/05-domain-model.md`. Proceed only when explicitly requested.

No code and no additional documentation will be produced until then.

---

*Nursilo — Learn. Practice. Succeed.*
