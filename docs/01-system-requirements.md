# Nursilo — System Requirements

| Field | Value |
| --- | --- |
| Document | `01-system-requirements.md` |
| Version | `1.0.0` |
| Status | **Approved** — locked requirements baseline |
| Product | Nursilo |
| Domain | https://nursilo.ahmad.bd |
| Depends on | [`00-project-vision.md`](00-project-vision.md) (Approved v1.0.0) |
| Audience | Product owners, architects, engineers, QA, future stakeholders |
| Next gated doc | `02-feature-list.md` (only after explicit confirmation of this locked document) |

---

## 1. Purpose

This document defines the **system requirements** for Nursilo Version 1: a Bangladesh-first, freemium B2C **Nursing Learning Ecosystem**.

It translates the approved Project Vision into testable functional and non-functional requirements. It does **not** prescribe database schemas, Django app layouts, UI wireframes, or API contracts—those belong in later gated documents.

**Core domain:** The **Assessment System** (Question Bank + Practice + Exam + Review + Analytics) is the product's core domain. Learning content supports exam preparation; there is no certificate module.

---

## 2. Scope

### 2.1 In scope (Version 1)

- Individual learner (B2C) web application
- Freemium access model (free core + premium unlocks)
- Bangla and English support without duplicating database tables
- Content hierarchy: Course → Subject → Unit → Chapter → Topic → Lesson → Learning Material → Question Bank → Practice → Exam → Analytics
- Assessment System as the primary product capability
- Multi-format Book Library (PDF, EPUB, HTML articles, image-based resources)
- Student dashboard, bookmarks, personal notes, notifications
- Global search across courses, books, lessons, questions, and authors
- Blog and public CMS pages (SEO-friendly)
- Admin/content operations with editorial workflow
- Subscription and entitlement enforcement (payment gateway integration may be phased; see FR-SUB)
- API-first business logic reusable by Django Templates (V1) and future Flutter clients
- Production-ready deployment posture for cPanel Passenger + Cloudflare + PostgreSQL

### 2.2 Out of scope (Version 1)

Aligned with vision non-goals:

- Certificates or certificate modules
- Institutional plans (colleges, hospitals, coaching centers)
- AI tutor / adaptive learning product features (architecture must remain AI-ready)
- Dedicated clinical case simulation mode
- Flutter apps and PWA / offline-first
- Full centralized media library product surface (foreshadowed only)
- OSCE preparation, nursing procedures modules, flashcards, medical calculators
- Redis, Celery, Cloudflare R2 unless later justified
- International payment providers as primary checkout

---

## 3. Definitions and Conventions

Terms follow the Glossary in `00-project-vision.md`. Additional conventions:

| ID prefix | Meaning |
| --- | --- |
| **FR-*** | Functional requirement |
| **NFR-*** | Non-functional requirement |
| **CON-*** | Constraint |
| **ASM-*** | Assumption |

Priority:

| Priority | Meaning |
| --- | --- |
| **Must** | Required for Version 1 acceptance |
| **Should** | Strongly expected; defer only with explicit approval |
| **Could** | Desirable if schedule allows; not blocking |

---

## 4. Stakeholders

| Stakeholder | Interest |
| --- | --- |
| Individual learners (students, interns, RNs) | Learn, practice, pass exams |
| Exam-track candidates (govt job, NCLEX, Prometric) | Specialized prep under premium |
| Super Admin / Admin | Platform operations and integrity |
| Editor / Reviewer / Author | Content quality and publication |
| Product / engineering | Maintainable, secure, API-ready system |

---

## 5. Assumptions and Constraints

### 5.1 Assumptions

| ID | Assumption |
| --- | --- |
| ASM-01 | Primary users access Nursilo via modern mobile and desktop browsers. |
| ASM-02 | Content is created/curated by Nursilo staff and approved SMEs under editorial workflow. |
| ASM-03 | Bangla and English are the only V1 languages. |
| ASM-04 | Freemium limits (e.g., free practice quota) will be configured as platform settings, not hard-coded magic numbers in multiple places. |
| ASM-05 | Payment gateway go-live (bKash / Nagad / SSLCommerz) may follow initial content/assessment launch, but entitlement model must exist from day one. |
| ASM-06 | Version 1 optimizes for individual accounts only (no org tenancy). |

### 5.2 Constraints

| ID | Constraint |
| --- | --- |
| CON-01 | Stack: Python 3.13, Django 5, PostgreSQL, DRF, Templates + Tailwind + HTMX + Alpine.js, Chart.js. |
| CON-02 | Hosting target: cPanel Passenger, Cloudflare, PostgreSQL. |
| CON-03 | No certificate features may be introduced in V1. |
| CON-04 | Multilingual content must not duplicate tables per language. |
| CON-05 | Business rules must live in reusable services/domain layer (API-first), not only in templates/views. |
| CON-06 | Educational content must be reusable and composable, not duplicated across courses/exams. |
| CON-07 | Architecture must remain AI-ready without shipping AI features in V1. |

---

## 6. System Context

```text
[Learner Browser]
       │
       ▼
[Nursilo Web — Django Templates + HTMX + Alpine]
       │
       ▼
[Domain Services — Assessment, Learning, Library, Entitlements, Search, CMS]
       │
       ├── [PostgreSQL]
       ├── [Media / file storage]
       └── [Future: DRF API → Flutter]
              │
[Admin / Author / Reviewer / Editor]
       │
       ▼
[Admin Panel + Editorial Workflow]
```

External (when enabled): payment gateways (bKash, Nagad, SSLCommerz), Cloudflare, email/notification providers.

---

## 7. Functional Requirements

### 7.1 Identity and accounts

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-ACC-01 | Users must be able to register an individual account. | Must |
| FR-ACC-02 | Users must be able to authenticate (login/logout) securely. | Must |
| FR-ACC-03 | Users must be able to reset a forgotten password. | Must |
| FR-ACC-04 | Users must be able to view and update basic profile information. | Must |
| FR-ACC-05 | The system must support role assignment among Super Admin, Admin, Editor, Reviewer, Author, and Student. | Must |
| FR-ACC-06 | Students must not access admin/content authoring surfaces. | Must |
| FR-ACC-07 | Users must be able to maintain an academic profile including: Academic Program, Institution, Current Semester/Year, Expected Graduation Year (optional), and Current Study Goal (optional), to support better analytics and personalized learning later. | Must |

### 7.2 Localization (Bangla / English)

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-I18N-01 | Learners must be able to choose Bangla or English as UI language. | Must |
| FR-I18N-02 | Publishable educational content must support Bangla and English representations without separate tables per language. | Must |
| FR-I18N-03 | Missing translation for a field should degrade gracefully (fallback rules defined in architecture docs). | Should |
| FR-I18N-04 | Question language metadata must be stored and filterable. | Must |

### 7.3 Learning hierarchy and content

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-LRN-01 | The system must model Course → Subject → Unit → Chapter → Topic → Lesson → Learning Material. | Must |
| FR-LRN-02 | Learning objects must be linkable into the Assessment System (questions, practice, exams, analytics). | Must |
| FR-LRN-03 | Content must be reusable/composable across multiple parent contexts without duplication of source-of-truth records. | Must |
| FR-LRN-04 | Learners must browse and open published courses/subjects/topics/lessons according to entitlements. | Must |
| FR-LRN-05 | Learners must be able to continue learning from last position (Continue Learning). | Must |
| FR-LRN-06 | Learning progress at topic/lesson granularity must be trackable. | Must |
| FR-LRN-07 | Only **Published** content is visible to learners; Draft/Review/Approved/Archived follow editorial rules. | Must |
| FR-LRN-08 | Educational content must support many-to-many relationships where academically appropriate (for example, a question may belong to multiple topics; a lesson may relate to multiple subjects; a book may support multiple courses). Unnecessary one-to-one relationships must be avoided. | Must |
| FR-LRN-09 | Learning materials and related hierarchy content must support archival / soft deletion instead of permanent deletion. | Must |

### 7.4 Editorial workflow

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-EDT-01 | Content lifecycle must support Draft → Review → Approved → Published → Archived. | Must |
| FR-EDT-02 | Authors can create/edit Draft content within permitted types. | Must |
| FR-EDT-03 | Reviewers can accept or reject content in Review. | Must |
| FR-EDT-04 | Editors/Admins can publish Approved content and archive Published content. | Must |
| FR-EDT-05 | Status transitions must be auditable (who/when). | Should |
| FR-EDT-06 | Content sources/attribution fields must be supportable for learning objects and books. | Should |
| FR-EDT-07 | Editors, Reviewers, and Admins must be able to preview unpublished content before publishing. | Must |

### 7.5 Assessment System — Question Bank (core)

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-QB-01 | The Question Bank must support: MCQ, True/False, Best Answer, Clinical Scenario Questions, Image-Based Questions. | Must |
| FR-QB-02 | Each question must support: stem, options (as applicable), correct answer(s), detailed explanation, reference book, difficulty, topic/chapter/subject/course linkage, language, tags. | Must |
| FR-QB-03 | Difficulty must be one of: Easy, Medium, Hard, Expert. | Must |
| FR-QB-04 | Questions must support bookmarking by learners. | Must |
| FR-QB-05 | Learners must be able to report an error on a question. | Must |
| FR-QB-06 | Staff must be able to triage and resolve reported errors. | Must |
| FR-QB-07 | Questions must respect editorial workflow before learner visibility. | Must |
| FR-QB-08 | Image-Based and Clinical Scenario Questions must support associated media/case text. | Must |
| FR-QB-09 | Question reuse across practice modes and exams must not require duplicating the question record. | Must |
| FR-QB-10 | Future edits to questions must not invalidate or alter historical exam attempts; the architecture must support question versioning or an equivalent immutable-attempt strategy. | Must |
| FR-QB-11 | During content creation, the system should help identify potential duplicate questions. | Should |
| FR-QB-12 | Questions must support archival / soft deletion instead of permanent deletion. | Must |

### 7.6 Assessment System — Practice (core)

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-PRC-01 | Learners must practice by Topic, Chapter, and Subject. | Must |
| FR-PRC-02 | Learners must access Random Practice within entitlement rules. | Must |
| FR-PRC-03 | Learners must create Custom Practice/Exams from filters (topic, difficulty, count, etc.). | Must |
| FR-PRC-04 | Free-tier practice volume must be enforceable via configurable limits. | Must |
| FR-PRC-05 | Practice sessions must record answers, correctness, and timing where applicable. | Must |
| FR-PRC-06 | After practice, learners must review answers with explanations (per entitlement). | Must |

### 7.7 Assessment System — Exam (core)

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-EXM-01 | The system must support Chapter Exams, Subject Exams, Timed Exams, and Mock Tests. | Must |
| FR-EXM-02 | Timed exams must enforce duration and submission on timeout. | Must |
| FR-EXM-03 | Mock tests must be configurable (blueprint, length, timing, entitlement). | Must |
| FR-EXM-04 | Exam attempts must persist score, breakdown, and completion status. | Must |
| FR-EXM-05 | Premium tracks must support Licensing, Government Job, NCLEX, and Prometric preparation exam sets. | Must |
| FR-EXM-06 | Unlimited mock exams must be available only to entitled premium users. | Must |
| FR-EXM-07 | Learners must be prevented from bypassing entitlements via direct URLs or API calls. | Must |
| FR-EXM-08 | Completed exam attempts must be permanently stored (unless removed according to future retention policies) so users can review their learning history over time. | Must |

### 7.8 Assessment System — Review (core)

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-REV-01 | Learners must review wrong answers from past attempts. | Must |
| FR-REV-02 | Learners must review bookmarked questions. | Must |
| FR-REV-03 | Review views must show correct answer and explanation when policy allows. | Must |

### 7.9 Assessment System — Analytics (core)

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-ANL-01 | The system must track study progress and exam history per learner. | Must |
| FR-ANL-02 | The system must identify weak topics and strong topics from attempt data. | Must |
| FR-ANL-03 | Advanced analytics must be premium-gated; basic progress may be free. | Must |
| FR-ANL-04 | Dashboard analytics visualizations must be supported (Chart.js on web). | Should |
| FR-ANL-05 | Analytics data model must remain suitable for future AI tutor / adaptive learning (AI-ready). | Must |

### 7.10 Book Library

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-LIB-01 | Books must support metadata: category, subject, author, edition, publisher, cover image. | Must |
| FR-LIB-02 | Library must support formats: PDF, EPUB, HTML articles, image-based resources. | Must |
| FR-LIB-03 | Learners must read entitled books online. | Must |
| FR-LIB-04 | Premium books must be entitlement-gated. | Must |
| FR-LIB-05 | Learners must bookmark books/positions where format allows. | Should |
| FR-LIB-06 | Books must be searchable and appear in global search. | Must |
| FR-LIB-07 | Downloadable books and resources must follow entitlement rules and access permissions; downloads must not bypass freemium or role restrictions. | Must |
| FR-LIB-08 | Books and library resources must support archival / soft deletion instead of permanent deletion. | Must |

### 7.11 Student dashboard and engagement

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-DSH-01 | Dashboard must include Continue Learning, Today's Goal, Study Progress, Exam History. | Must |
| FR-DSH-02 | Dashboard must surface Weak Topics, Strong Topics, Bookmarks, Saved Notes, Recent Activity. | Must |
| FR-DSH-03 | Dashboard must show Study Streak, Subscription Status, and Notifications summary. | Must |
| FR-DSH-04 | Learners must create/edit/delete personal notes linked to learning objects or questions. | Must |
| FR-DSH-05 | Learners must manage bookmarks for questions and learning content. | Must |
| FR-DSH-06 | In-app notifications must inform learners of relevant system/content events. | Should |

### 7.12 Global search

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-SRCH-01 | Global search must query across courses, books, lessons, questions, and authors. | Must |
| FR-SRCH-02 | Search results must respect publish state and entitlements (no leakage of premium-only payloads beyond allowed teasers). | Must |
| FR-SRCH-03 | Search must support Bangla and English queries at a basic competence level for V1. | Should |

### 7.13 Blog and public CMS

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-CMS-01 | Public marketing/landing pages must be manageable. | Must |
| FR-CMS-02 | Blog posts must be creatable, publishable, and publicly readable. | Must |
| FR-CMS-03 | Public pages must be SEO-friendly (titles, meta, clean URLs, indexable content). | Must |

### 7.14 Subscriptions and payments

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-SUB-01 | The system must model Free vs Premium entitlements centrally. | Must |
| FR-SUB-02 | Premium must unlock: complete question bank, unlimited mocks, licensing/govt/NCLEX/Prometric prep, premium books/notes, advanced analytics. | Must |
| FR-SUB-03 | Entitlement checks must be enforced in domain services used by web and future API. | Must |
| FR-SUB-04 | Subscription status must be visible on the student dashboard. | Must |
| FR-SUB-05 | Payment integration must prioritize bKash, Nagad, and SSLCommerz when payments go live. | Must (when payments enabled) |
| FR-SUB-06 | Payment webhooks/callbacks must be verified; entitlements activate only after confirmed payment. | Must (when payments enabled) |
| FR-SUB-07 | Manual/admin grant of premium must be supported for support operations. | Should |

### 7.15 Administration

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-ADM-01 | Admins must manage users, roles, courses hierarchy, books, question bank, exams, mocks, blog, CMS pages, notifications, subscriptions, payments, website settings, analytics, and logs. | Must |
| FR-ADM-02 | Role capabilities must follow least privilege (detailed in `03-user-roles.md`). | Must |
| FR-ADM-03 | The system must maintain audit logs for: login events, role changes, content publication, question edits, subscription changes, and payment events (in addition to other critical admin actions). | Must |
| FR-ADM-04 | The system must support structured bulk import/export of questions, learning materials, and books (essential for large-scale content operations). | Must |
| FR-ADM-05 | Important content types (learning materials, books, questions, and equivalents) must prefer archival / soft deletion over permanent deletion. | Must |

### 7.16 Explicitly excluded functions

| ID | Requirement |
| --- | --- |
| FR-XCL-01 | The system must not issue course certificates or provide a certificate module. |
| FR-XCL-02 | The system must not implement institutional tenancy or seat licensing in V1. |

---

## 8. Non-Functional Requirements

### 8.1 Security

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-SEC-01 | Protect against common web threats (CSRF, XSS, injection, auth abuse). | Must |
| NFR-SEC-02 | Passwords stored with strong hashing; secrets not in source control. | Must |
| NFR-SEC-03 | Authorization enforced server-side for every privileged action. | Must |
| NFR-SEC-04 | Entitlement bypass attempts must fail closed. | Must |
| NFR-SEC-05 | Admin surfaces must be restricted to staff roles. | Must |
| NFR-SEC-06 | Payment-related endpoints must validate authenticity and idempotency. | Must (when payments enabled) |

### 8.2 Performance

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-PRF-01 | Typical learner page views should respond within acceptable interactive times on target hosting (specific SLOs in deployment plan). | Should |
| NFR-PRF-02 | Exam attempt submission must be reliable under concurrent learner use for expected V1 scale. | Must |
| NFR-PRF-03 | List/search queries must use efficient PostgreSQL access patterns (indexes, pagination). | Must |
| NFR-PRF-04 | Performance by design: avoid N+1 queries on hierarchy and attempt review screens. | Must |

### 8.3 Reliability and operations

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-OPS-01 | Production configuration must separate secrets, debug flags, and allowed hosts correctly. | Must |
| NFR-OPS-02 | Database backups and restore procedure must be defined before production launch. | Must |
| NFR-OPS-03 | Application logging must capture errors and audit events including login events, role changes, content publication, question edits, subscription changes, and payment events. | Must |
| NFR-OPS-04 | Cloudflare should be used for DNS/CDN/security posture as planned in deployment docs. | Should |

### 8.4 Usability, accessibility, responsiveness

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-UX-01 | UI must be responsive for common mobile and desktop viewports. | Must |
| NFR-UX-02 | Primary learner flows (practice, exam, review) must be completable on mobile browsers. | Must |
| NFR-UX-03 | Forms and interactive controls should follow accessible labeling and keyboard usability basics. | Should |

### 8.5 SEO

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-SEO-01 | Public pages (home, marketing, blog, public course teasers as applicable) must expose crawlable content and correct metadata. | Must |
| NFR-SEO-02 | Authenticated app areas should be non-indexed where appropriate. | Should |

### 8.6 Maintainability and architecture quality

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-ARC-01 | Modular Django apps with clear domain boundaries. | Must |
| NFR-ARC-02 | Business logic reusable beyond templates (API-first). | Must |
| NFR-ARC-03 | Follow Django best practices; apply Clean Architecture / SOLID where practical without unnecessary complexity. | Must |
| NFR-ARC-04 | Multilingual design without duplicated tables. | Must |
| NFR-ARC-05 | AI-ready data and service boundaries for future tutor/adaptive features. | Must |
| NFR-ARC-06 | Educational content relationships must support many-to-many associations where academically appropriate; avoid forcing unnecessary one-to-one relationships. | Must |
| NFR-ARC-07 | Question versioning (or equivalent) must preserve historical exam attempt integrity when question content changes. | Must |
| NFR-ARC-08 | Soft delete / archival patterns must be the default for important educational content rather than hard delete. | Must |

### 8.7 Compliance and content integrity

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-CNT-01 | Published educational content must pass editorial workflow. | Must |
| NFR-CNT-02 | Rights/attribution for licensed materials must be representable. | Should |
| NFR-CNT-03 | Learner personal notes and account data must be private to the account. | Must |

---

## 9. Freemium Entitlement Matrix (Requirements View)

| Capability | Free | Premium |
| --- | --- | --- |
| Account + dashboard basics | Yes | Yes |
| Core learning materials | Yes | Yes |
| Limited practice | Yes (capped) | Yes (uncapped per plan rules) |
| Complete question bank | No | Yes |
| Unlimited mock exams | No | Yes |
| Licensing / Govt / NCLEX / Prometric tracks | No (or teaser only) | Yes |
| Premium books and notes | No | Yes |
| Advanced analytics | No | Yes |
| Wrong-answer / bookmark review | Basic as policy allows | Full |
| Future offline/PWA | N/A in V1 | Future |

Exact numeric caps and plan SKUs will be specified in feature/subscription docs; this matrix is the requirements baseline.

---

## 10. Data and Traceability Notes

- Attempt, bookmark, note, and progress data are learner-owned and must not leak across accounts.
- Question and learning objects are shared catalog content governed by publish state and entitlements.
- Requirement IDs in this document are the traceability keys for `02-feature-list.md`, tests, and later architecture decisions.
- Assessment System requirements (FR-QB, FR-PRC, FR-EXM, FR-REV, FR-ANL) take precedence when prioritization conflicts arise with secondary features.

---

## 11. Acceptance Criteria (Document Level)

This requirements baseline is acceptable when:

1. Assessment System coverage is complete for V1 practice/exam/review/analytics.
2. Freemium rules and explicit exclusions (no certificates; no institutions) are unambiguous.
3. Bangla/English and API-first constraints are explicit.
4. Non-functional expectations cover security, performance, SEO, responsiveness, and production readiness.
5. Out-of-scope future items are listed without being treated as V1 delivery commitments.

---

## 12. Document Lock

**Status:** `docs/01-system-requirements.md` is **Approved** and locked at **Version 1.0.0**.

All requested refinements (academic profile, permanent exam history, question versioning, soft delete, expanded audit logging, draft preview, bulk import/export, duplicate detection, download permissions, and many-to-many content relationships) are incorporated.

Proceed to `docs/02-feature-list.md` **only when explicitly requested and after confirmation of this locked document**. Document 02 must be authored as a product backlog where every feature includes: Module, Feature, Description, Priority (Must/Should/Could), Dependencies, User Roles, Version (V1/Future), and Acceptance Criteria.

No code and no additional documentation will be produced until then.

---

*Nursilo — Learn. Practice. Succeed.*
