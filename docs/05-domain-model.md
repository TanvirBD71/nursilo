# Nursilo — Domain Model

| Field | Value |
| --- | --- |
| Document | `05-domain-model.md` |
| Version | `1.0.0` |
| Status | **Approved** — locked domain model |
| Product | Nursilo |
| Depends on | [`00-project-vision.md`](00-project-vision.md) … [`04-system-architecture.md`](04-system-architecture.md) (Approved v1.0.0) |
| Purpose | Define entities, aggregate roots, value objects, ownership boundaries, and domain relationships—**without** database tables |
| Next gated doc | `06-database-design.md` |

---

## 1. Purpose

This document is the **ubiquitous language and domain model** for Nursilo. It defines what exists in the business, what is an aggregate root, what is a value object, who owns which invariants, and how domains relate.

It deliberately does **not** define:

- Database tables, columns, indexes, or ERDs  
- Django models or migrations  
- API payloads  
- UI screens  
- Implementation code  

Database design must follow **only after** this Domain Model is approved.

---

## 2. Modeling Conventions

| Term | Meaning |
| --- | --- |
| **Entity** | An object with identity that persists over time |
| **Aggregate root** | The entry entity for a consistency boundary; external references should point to the root |
| **Value object** | Immutable (or replace-as-whole) descriptive concept without independent lifecycle identity in the domain |
| **Domain relationship** | Conceptual association (1:1, 1:N, M:N)—not a foreign-key design |
| **Ownership boundary** | Which aggregate/context may mutate which invariants |

**Core domain reminder:** The Assessment System (Question Bank + Practice + Exam + Review + Analytics signals) is the product core. Learning content supports assessment.

---

## 3. Bounded Context Ownership Map

| Context | Aggregate roots (primary) | Key supporting entities |
| --- | --- | --- |
| Identity | `UserAccount` | `AcademicProfile`, `RoleAssignment` |
| Entitlements & Billing | `Subscription` | `PaymentTransaction`, `EntitlementGrant` |
| Learning Catalog | `Course` (hierarchy via children) | `Subject`, `Unit`, `Chapter`, `Topic`, `Lesson`, `LearningMaterial` |
| Assessment Catalog | `Question` | `QuestionVersion`, `QuestionOption`, `Tag`, `QuestionErrorReport` |
| Assessment Runtime | `Attempt` | `AttemptItem`, `ExamDefinition`, `PracticeSession` (or Attempt subtypes) |
| Library | `Book` | `BookFormatAsset`, `BookBookmark` |
| Engagement | `PersonalNote`, `Bookmark`, `StudyGoal`, `StudyStreak` | — |
| Notifications | `Notification`, `Announcement` | — |
| CMS | `CmsPage`, `BlogPost`, `ContactMessage` | — |
| Search | *(no write aggregate)* | `SearchDocument` (read projection) |
| Analytics | *(derived)* | `LearnerTopicStat`, `QuestionUsageStat` (read models) |
| Platform | `PlatformSetting`, `AuditEvent` | `FeatureToggle` |

---

## 4. Shared Value Objects

Used across contexts (conceptual; not shared DB tables):

| Value object | Description |
| --- | --- |
| `LocaleCode` | `bn` / `en` (Bangla / English) |
| `LocalizedText` | Text payload for a locale (pair/map conceptually) |
| `EditorialState` | Draft \| Review \| Approved \| Published \| Archived |
| `DifficultyLevel` | Easy \| Medium \| Hard \| Expert |
| `CapabilityCode` | Named freemium capability (e.g., unlimited mocks, premium books) |
| `MoneyAmount` | Amount + currency for payment facts |
| `TimeWindow` | Start/end or duration for timed exams |
| `Slug` | Public identity fragment for CMS/SEO |
| `ContentReference` | Pointer to a catalog object type + identity (for notes/bookmarks/search) |
| `SoftDeleteMark` | Archived/active semantic (not a hard delete) |

---

## 5. Identity & Access

### 5.1 Aggregate: `UserAccount` (root)

| Element | Kind | Notes |
| --- | --- | --- |
| `UserAccount` | Aggregate root | Authenticatable principal |
| `PersonName` / profile fields | Attributes / VOs | Basic profile |
| `AcademicProfile` | Entity inside aggregate (or tightly owned child) | Program, institution, semester/year, optional graduation year, optional study goal |
| `RoleAssignment` | Entity | Links account to RBAC role (Super Admin…Student) |
| `UiLocalePreference` | Value object | Bangla/English UI |

**Invariants**

- A Student cannot hold staff console access through Student role alone.  
- Academic profile is optional field-wise but owned by the account.  
- Role changes are auditable facts (emit/record via Platform audit).

**Relationships**

- `UserAccount` 1 — 0..1 `AcademicProfile`  
- `UserAccount` 1 — N `RoleAssignment` (V1 typically one primary role)  
- `UserAccount` referenced by Attempts, Notes, Subscriptions (by identity only)

---

## 6. Entitlements & Billing

### 6.1 Aggregate: `Subscription` (root)

| Element | Kind | Notes |
| --- | --- | --- |
| `Subscription` | Aggregate root | Effective Free / PendingPayment / PremiumActive / Expired / Revoked |
| `PlanTier` | Value object | Free vs Premium (extensible later) |
| `EntitlementGrant` | Entity | Capability set effective for a period |
| `PaymentTransaction` | Entity (or related aggregate) | Gateway attempt + verification state |
| `ManualGrantRecord` | Entity | Audited Admin/Super Admin grant/revoke |

**Invariants**

- Premium capabilities require `PremiumActive` (or equivalent grant).  
- `PaymentConfirmed` activates entitlement idempotently.  
- Assessment/Library never own payment verification.

**Relationships**

- `UserAccount` 1 — 0..1 effective `Subscription` (or 1—N historical; one effective)  
- `PaymentTransaction` N — 1 `Subscription` / `UserAccount`

---

## 7. Learning Catalog

Hierarchy (composition with reusable links):

```text
Course
  └─ Subject
       └─ Unit
            └─ Chapter
                 └─ Topic
                      └─ Lesson
                           └─ LearningMaterial
```

### 7.1 Aggregate roots

| Root | Owns | Rationale |
| --- | --- | --- |
| `Course` | Course-level metadata, ordered Subjects membership, editorial state at course scope as policy defines | Top learning program boundary |
| `LearningMaterial` | Material body, media refs, editorial state | Reusable composable asset—may be linked from multiple lessons |

**Practical V1 modeling note (conceptual):** Hierarchy nodes (`Subject`…`Lesson`) are **entities** with identity. Consistency for renaming/ordering is usually enforced per subtree transaction; publishing visibility is governed by `EditorialState` on each publishable node. Avoid forcing a single giant aggregate for the entire university-sized tree.

### 7.2 Entities

| Entity | Meaning |
| --- | --- |
| `Subject`, `Unit`, `Chapter`, `Topic`, `Lesson` | Structural learning nodes |
| `LearningMaterial` | Notes/media/readings asset |
| `LearnerProgress` | Per-user pointer/completion at lesson/topic granularity |
| `ContinueLearningCursor` | Last position for resume |

### 7.3 Relationships

| Relationship | Cardinality | Note |
| --- | --- | --- |
| Course — Subject | 1—N (ordered) | Standard hierarchy |
| Subject — Unit — Chapter — Topic — Lesson | 1—N each | Ordered |
| Lesson — LearningMaterial | M—N | Reuse materials |
| Lesson — Subject | M—N (optional extra) | When academically appropriate beyond strict tree |
| Topic — Question | M—N | Assessment linkage |
| Course — Book | M—N | Library support |

**Invariants**

- Learners discover only `Published` nodes.  
- Soft delete/archive removes from discovery without destroying history.  
- Progress belongs to the learner identity, not to the catalog aggregate.

---

## 8. Assessment Catalog (Core)

### 8.1 Aggregate: `Question` (root)

| Element | Kind | Notes |
| --- | --- | --- |
| `Question` | Aggregate root | Stable identity across edits |
| `QuestionVersion` | Entity | Immutable (or append-only) version used by attempts |
| `QuestionStem` | Localized content VO/entity | Stem text per locale |
| `QuestionOption` | Entity | Options for MCQ/Best Answer/T-F as applicable |
| `CorrectAnswerSpec` | Value object | Correctness definition for the version |
| `Explanation` | Localized content | Detailed explanation |
| `ReferenceCitation` | Value object | Reference book / citation |
| `DifficultyLevel` | Value object | Easy…Expert |
| `QuestionType` | Value object | MCQ, TrueFalse, BestAnswer, ClinicalScenario, ImageBased |
| `ClinicalScenarioBody` | Content | Case text for Clinical Scenario Questions |
| `MediaAssetRef` | Value object | Image/media for image-based items (access mediated) |
| `Tag` | Entity (shared catalog) | Labels; M—N with questions |
| `EditorialState` | Value object | Workflow state of current publishable revision |

**Invariants**

- Edits that change scored meaning create a **new `QuestionVersion`** (or equivalent); historical attempts keep prior version references.  
- Published visibility requires editorial publish rules.  
- Soft delete archives the question from pools; does not rewrite attempts.  
- Duplicate detection advises authors; it does not merge identities automatically.

### 8.2 Supporting entities

| Entity | Meaning |
| --- | --- |
| `QuestionErrorReport` | Learner report + triage state |
| `ExamDefinition` / `MockBlueprint` | Catalog configuration for structured exams (may be separate aggregate) |
| `PracticeTemplate` (V1.1) | Saved custom filters for a learner |

### 8.3 Relationships

| Relationship | Cardinality |
| --- | --- |
| Question — QuestionVersion | 1—N |
| QuestionVersion — QuestionOption | 1—N |
| Question — Topic | M—N |
| Question — Tag | M—N |
| Question — Course/Subject/Chapter | via topics/hierarchy links (derived or explicit M—N as needed) |
| Question — QuestionErrorReport | 1—N |
| ExamDefinition — Question (pool) | M—N through blueprint rules |

---

## 9. Assessment Runtime (Core)

### 9.1 Aggregate: `Attempt` (root)

| Element | Kind | Notes |
| --- | --- | --- |
| `Attempt` | Aggregate root | Practice or Exam instance for one learner |
| `AttemptMode` | Value object | Practice \| ChapterExam \| SubjectExam \| TimedExam \| Mock \| Custom |
| `AttemptState` | Value object | NotStarted \| InProgress \| Submitted \| Completed |
| `TimeWindow` / remaining duration | Value object / attribute | Server-authoritative for timed modes |
| `AttemptItem` | Entity | One presented question slot |
| `SelectedAnswer` | Value object | Learner response |
| `ItemResult` | Value object | Correctness after scoring |
| `QuestionVersionRef` | Value object | Frozen reference for integrity |
| `ScoreSummary` | Value object | Score, breakdown, counts |

**Invariants**

- Resume only from `InProgress`.  
- Completed attempts are historically durable (no casual user delete in V1).  
- Scoring uses the referenced `QuestionVersion`, not the latest stem.  
- Start/submit require entitlement + publish checks.  
- Free practice caps enforced when opening Practice-mode attempts.

### 9.2 Related concepts

| Concept | Kind | Notes |
| --- | --- | --- |
| `PracticeSession` | Alias/subtype of Attempt or thin aggregate | Formative mode policies |
| `ExamAttempt` | Alias/subtype of Attempt | Timed/mock policies |
| Wrong-answer Review projection | Read model | Derived from AttemptItems |
| Bookmark Review | Uses Engagement `Bookmark` + catalog | Not part of Attempt aggregate |

**Relationships**

- `UserAccount` 1 — N `Attempt`  
- `Attempt` 1 — N `AttemptItem`  
- `AttemptItem` N — 1 `QuestionVersion`  

---

## 10. Book Library

### 10.1 Aggregate: `Book` (root)

| Element | Kind | Notes |
| --- | --- | --- |
| `Book` | Aggregate root | Catalog identity + metadata |
| Metadata | Attributes/VOs | Category, subject, author, edition, publisher, cover |
| `BookFormatAsset` | Entity | PDF / EPUB / HTML / image-based resource |
| `EditorialState` | Value object | Lifecycle |
| `PremiumFlag` | Value object/attribute | Entitlement gating |
| `BookBookmark` | Entity (learner-owned; see Engagement) | Optional position |

**Relationships**

- `Book` — `Course` M—N  
- `Book` — `BookFormatAsset` 1—N  
- Read/download authorization is a **domain service decision**, not a Book attribute alone  

**Invariants**

- Download/read require entitlement + Published state.  
- Soft delete archives from catalog discovery.

---

## 11. Engagement

Learner-owned aggregates (separate from catalog):

| Aggregate root | Owns | Relationships |
| --- | --- | --- |
| `PersonalNote` | Note body + `ContentReference` | N per UserAccount |
| `Bookmark` | Reference to question/content/book | N per UserAccount |
| `StudyGoal` | Daily/period goal definition + progress | Per UserAccount |
| `StudyStreak` | Streak counters/dates | Per UserAccount |

**Invariants:** Private to owning learner; staff do not browse casually via Student permissions.

---

## 12. Notifications & Announcements

| Aggregate root | Meaning |
| --- | --- |
| `Notification` | Per-recipient in-app message (read/unread) |
| `Announcement` | Staff-authored broadcast/targeted message with publish state |

**Relationships:** `Announcement` may fan out to many `Notification` records (sync in V1).

---

## 13. CMS & Communications

| Aggregate root | Meaning |
| --- | --- |
| `CmsPage` | Marketing/landing page + SEO value objects |
| `BlogPost` | Blog article + SEO + editorial state |
| `ContactMessage` | Contact/feedback submission + triage state |

Public readability applies only to Published CMS content.

---

## 14. Search & Analytics (Read Models)

Not authoritative write models:

| Read model | Built from | Used for |
| --- | --- | --- |
| `SearchDocument` | Published catalog events | Global search |
| `LearnerTopicStat` | Attempt results | Weak/strong topics |
| `QuestionUsageStat` | Attempt items | Attempt count, accuracy, difficulty trend |
| `ContentPerformanceStat` | Progress + engagement signals | Admin content analytics |

**Rule:** Read models may be rebuilt; they must not become the source of truth for scoring or entitlements.

---

## 15. Platform

| Aggregate / entity | Meaning |
| --- | --- |
| `PlatformSetting` | Non-secret configuration values |
| `FeatureToggle` | Named capability switch |
| `AuditEvent` | Append-only privileged action record |

**Invariants:** Audit events are not editable by Admin; Super Admin boundaries apply to security/payment toggles.

---

## 16. Content Lifecycle (Shared Pattern)

Publishable catalog entities share the editorial value object:

```text
Draft → Review → Approved → Published → Archived
```

Applies conceptually to: learning nodes/materials, questions (current revision), books, CMS posts/pages, announcements (as applicable).

Staff preview references the unpublished entity **without** changing Student visibility rules.

---

## 17. Cross-Context Relationship Diagram (Conceptual)

```text
UserAccount
 ├── AcademicProfile
 ├── RoleAssignment
 ├── Subscription ── PaymentTransaction
 ├── Attempt ── AttemptItem ── QuestionVersion ── Question
 ├── PersonalNote / Bookmark / StudyGoal / StudyStreak
 └── Notification

Course ── Subject ── Unit ── Chapter ── Topic ── Lesson ── LearningMaterial
                         │                 │
                         │                 └──<<M:N>>── Question
                         └──<<M:N>>── Book ── BookFormatAsset

ExamDefinition / MockBlueprint ── (selects) → Question pool
Announcement ──► Notification
Catalog publish events ──► SearchDocument
Attempt completion ──► LearnerTopicStat / QuestionUsageStat
```

---

## 18. Aggregate Integrity Rules (Summary)

| Rule | Statement |
| --- | --- |
| Attempt integrity | Attempts reference `QuestionVersion`, not mutable head content alone |
| Entitlement boundary | Capability checks live outside catalog aggregates |
| Soft delete | Archive semantics on catalog roots; runtime history retained |
| M2N first | Prefer academically valid many-to-many over forced one-to-one |
| Composability | Materials/questions are reusable; do not duplicate source identities per course |
| Student isolation | Learner private aggregates are not part of staff editing aggregates |
| Projection purity | Search/analytics are derived |

---

## 19. Mapping to Architecture Services

| Aggregate / concept | Primary service |
| --- | --- |
| UserAccount / AcademicProfile | AccountService |
| RoleAssignment | AccessControlService |
| Subscription / Payment | BillingService + EntitlementService |
| Course…Lesson / Material | LearningCatalogService + EditorialWorkflowService |
| Question / Version | QuestionBankService |
| Attempt | PracticeService / ExamService |
| Book | LibraryService |
| SearchDocument | SearchService |
| Stats | AnalyticsService |
| Notification / Announcement | NotificationService |
| AuditEvent / toggles | AuditService / SettingsService |

---

## 20. Explicit Non-Objects (V1)

| Not in V1 domain |
| --- |
| Certificate / CertificateIssuance |
| Institution / SeatLicense / Cohort (Future) |
| AITutorSession (Future) |
| FlashcardDeck / MedicalCalculator (Future) |
| DiscussionThread on questions (Future) |

---

## 21. Aggregate Domain Events Ownership

Domain events are **facts** recorded after an aggregate successfully enforces its invariants. They describe what already happened on the owning aggregate—not commands to mutate another aggregate's internals.

| Domain event | Owning aggregate / side | Meaning (after successful invariants) |
| --- | --- | --- |
| `QuestionPublished` | `Question` | Current publishable revision is visible under publish rules |
| `QuestionArchived` | `Question` | Question removed from learner pools; history retained |
| `AttemptStarted` | `Attempt` | Attempt entered `InProgress` for a learner |
| `AttemptCompleted` | `Attempt` | Attempt reached terminal completed/submitted scoring state |
| `ExamCompleted` | `Attempt` (exam mode) | Exam-mode completion fact (subtype of attempt completion) |
| `PracticeCompleted` | `Attempt` (practice mode) | Practice-mode completion fact (subtype of attempt completion) |
| `SubscriptionActivated` | `Subscription` | Effective premium (or plan) entitlement became active |
| `SubscriptionChanged` | `Subscription` | Plan/tier/state change after billing or admin grant rules |
| `ContentPublished` | Learning catalog / CMS publishable root | Catalog or CMS node became `Published` |
| `ContentArchived` | Learning catalog / CMS publishable root | Soft-archive; hidden from learner discovery |
| `AnnouncementPublished` | `Announcement` | Broadcast/targeted announcement entered published state |
| `QuestionErrorReported` | `Question` (via `QuestionErrorReport`) | Learner error report accepted against a question |
| `PaymentConfirmed` | Billing / `Subscription` side | Payment verification succeeded; may drive entitlement activation |

**Note:** `ExamCompleted` / `PracticeCompleted` are mode-specific completion facts owned by the `Attempt` aggregate (alongside or as refinements of `AttemptCompleted`). `PaymentConfirmed` is owned by the billing/subscription side—not by Assessment or Library aggregates.

---

## 22. Aggregate Size Rule

Aggregates remain **intentionally small**.

Do **not** grow an aggregate to own unrelated large object graphs:

| Anti-pattern | Correct approach |
| --- | --- |
| `Question` owns all `Attempt`s | `Attempt` references `QuestionVersion` by identity |
| `Course` owns the entire platform tree as one write unit | Hierarchy nodes keep identity; enforce consistency per practical subtree boundary |
| `Attempt` owns the Question catalog | `AttemptItem` holds `QuestionVersion` references only |
| Catalog root owns all learner progress/notes | Learner-owned aggregates reference catalog by identity |

**Prefer references by identity** across aggregate boundaries. Load and mutate one consistency boundary at a time.

---

## 23. Aggregate Ownership Rules

| Aggregate root | May mutate | Must not mutate |
| --- | --- | --- |
| `UserAccount` | Profile, academic profile, role assignments (within policy), UI locale | Subscription payment verification; Attempt scoring; Question stem versions |
| `Subscription` | Plan/state, entitlement grants, payment-linked activation (with billing facts) | Question bank content; Attempt answers; Learning catalog editorial state |
| `Question` | Versions, options, explanations, tags/links, editorial state, error-report triage on owned reports | Completed Attempt records; Subscription entitlements; unrelated Course hierarchy bodies |
| `Attempt` | Own lifecycle, items, selected answers, score summary for this attempt | Live Question catalog head; create new QuestionVersions; PaymentTransaction verification |
| `Course` / learning nodes / `LearningMaterial` | Owned metadata, ordering, editorial state, material body (per root policy) | Attempt history; Subscription; QuestionVersion immutability after attempt reference |
| `Book` | Metadata, format assets, editorial/premium flags | Payment confirmation; Attempt contents |
| Engagement roots (`PersonalNote`, `Bookmark`, …) | Owning learner's private state | Catalog publish state; other learners' private aggregates |
| `Announcement` / `Notification` | Own publish/read state | Assessment scoring; entitlements |
| CMS roots | Own page/post/contact triage state | Assessment runtime; billing |

---

## 24. Domain Invariants

Non-negotiable business truths (document-level):

| # | Invariant |
| --- | --- |
| 1 | A `QuestionVersion` referenced by completed attempts is **immutable** (no rewrite of scored meaning). |
| 2 | **Completed attempts are immutable** as historical facts (no casual learner delete in V1). |
| 3 | **Archived** catalog content is hidden from learner discovery/pools. |
| 4 | **Soft delete / archive is the default**; do not hard-destroy assessment or catalog history needed for integrity. |
| 5 | **Entitlement checks live outside** catalog aggregates (Billing/Entitlement services). |
| 6 | **Students never see unpublished** catalog/CMS content (staff preview is a separate RBAC path). |
| 7 | **Payment verification precedes premium** capability activation (`PaymentConfirmed` → entitlement). |
| 8 | **M:N is allowed** where academically required (topics↔questions, lessons↔materials, courses↔books, tags). |
| 9 | **No certificates** (or certificate issuance) in V1 domain. |
| 10 | Attempts score against referenced `QuestionVersion`, not mutable live stem alone. |
| 11 | Assessment/Library aggregates never own payment verification. |
| 12 | Read models (search/analytics) are derived and must not become scoring/entitlement source of truth. |
| 13 | Learner private aggregates are not part of staff catalog editing aggregates. |

---

## 25. Entity Identity

| Concept | Identity rule |
| --- | --- |
| `Question` id | **Stable** across editorial revisions; external references prefer this root when naming the item |
| `QuestionVersion` id | **Per revision**; frozen identity used by scoring and history |
| `Attempt` id | Stable identity for one practice/exam instance |
| `AttemptItem` | References **`QuestionVersion` id** (not only live Question head) |
| `UserAccount` id | Stable principal identity referenced by Attempts, Subscription, notes |
| `Subscription` id | Stable entitlement boundary identity for the account's billing lifecycle |
| Learning / Book / CMS ids | Stable catalog identities; editorial state changes do not redefine identity |

**Rule:** Cross-aggregate links use stable root or version identities as appropriate—never mutate another aggregate by reaching through a dangling internal child without going through the owning root's rules.

---

## 26. Aggregate Ownership Diagram

```text
UserAccount
  ├── (refs) Subscription ── PaymentTransaction / EntitlementGrant
  ├── (owns) Attempt ── AttemptItem ──(ref)── QuestionVersion
  │                                      └── Question (root)
  ├── (owns) PersonalNote / Bookmark / StudyGoal / StudyStreak
  └── (owns) Notification

Question (root)
  ├── QuestionVersion* (append-only / immutable when referenced)
  ├── QuestionOption / stem / explanation (per version)
  └── QuestionErrorReport

Course ── Subject ── Unit ── Chapter ── Topic ── Lesson
                                              └──(M:N)── LearningMaterial
                         Topic ──(M:N)── Question
Course ──(M:N)── Book ── BookFormatAsset

Announcement ──► Notification (fan-out)
Billing/Subscription side ── PaymentConfirmed / SubscriptionActivated
```

Edges labeled `(ref)` are identity references across aggregates. Edges without `(ref)` are ownership inside a consistency boundary (or hierarchy policy as defined in §7).

---

## 27. Cross-Aggregate Communication

Aggregates **communicate only through domain services** (application/domain orchestration).

| Allowed | Forbidden |
| --- | --- |
| Domain service loads Aggregate A, applies command, records events | Aggregate A reaches into Aggregate B's internal entities to mutate them |
| Domain service checks entitlement, then starts Attempt | `Attempt` directly flips `Subscription` state |
| Domain service publishes Question, then projects search | `Question` rewrites completed `AttemptItem` results |
| Billing confirms payment → activates `Subscription` | Library/Assessment verifies gateway payments themselves |

Orchestration may react to domain events, but **invariants remain enforced inside the owning aggregate** when that aggregate is loaded and saved.

---

## 28. Consolidated Aggregate Lifecycle Summary

### Question

| Phase | Notes |
| --- | --- |
| Draft / Review / Approved | Staff editorial on current revision |
| Published | Emits `QuestionPublished`; eligible for pools under rules |
| New version | Meaning-changing edit → new `QuestionVersion` |
| Archived | Emits `QuestionArchived`; hidden from learners; attempts retain old versions |

### Attempt

| Phase | Notes |
| --- | --- |
| NotStarted → InProgress | `AttemptStarted`; entitlement + publish checks |
| InProgress | Resume allowed; answers recorded on items |
| Submitted / Completed | `AttemptCompleted` (+ `ExamCompleted` / `PracticeCompleted` as mode facts); historically durable |

### Subscription

| Phase | Notes |
| --- | --- |
| Free / PendingPayment | Baseline or awaiting verification |
| PaymentConfirmed | Billing-side fact |
| PremiumActive | `SubscriptionActivated` / capability grants effective |
| Changed / Expired / Revoked | `SubscriptionChanged`; entitlements recalculated |

### Learning Content

| Phase | Notes |
| --- | --- |
| Draft → Review → Approved → Published | Shared editorial pattern; `ContentPublished` |
| Archived | `ContentArchived`; soft-hidden from discovery |
| Restore | Policy-defined re-entry to editorial cycle |

---

## 29. Acceptance Criteria (Document Level)

This Domain Model is acceptable when it:

1. Names aggregate roots for Identity, Subscription, Question, Attempt, Book, and major engagement/CMS objects  
2. Separates Assessment Catalog from Assessment Runtime for attempt integrity  
3. States M:N relationships for topics, materials, and books where academically required  
4. Defines shared editorial and difficulty/type value objects  
5. Clarifies read models vs write aggregates  
6. Defines **aggregate domain-event ownership** (§21)  
7. States the **aggregate size rule** and **ownership rules** (§22–§23)  
8. Lists **document-level domain invariants** (§24)  
9. Clarifies **entity identity** (stable roots vs version ids) (§25)  
10. Provides an **ownership diagram** and **cross-aggregate communication** rule (§26–§27)  
11. Summarizes **Question, Attempt, Subscription, and Learning Content lifecycles** (§28)  
12. Contains **no** database tables, schemas, Django models, or API contracts  

---

## 30. Document Lock

| Field | Value |
| --- | --- |
| Status | **Approved** — locked domain model **v1.0.0** |
| Lock meaning | Sections 1–30 are the approved ubiquitous language and aggregate boundaries for V1 |
| Next gated document | [`06-database-design.md`](06-database-design.md) |
| Rule | Database design and implementation proceed from this locked model; do not invent conflicting aggregates |

---

*Nursilo — Learn. Practice. Succeed.*
