# Nursilo — Product Backlog (Feature List)

| Field | Value |
| --- | --- |
| Document | `02-feature-list.md` |
| Version | `1.0.0` |
| Status | **Approved** — locked product backlog |
| Product | Nursilo |
| Depends on | [`00-project-vision.md`](00-project-vision.md) (Approved v1.0.0), [`01-system-requirements.md`](01-system-requirements.md) (Approved v1.0.0) |
| Purpose | Master product backlog for Version 1 planning and future roadmap tracking |
| Next gated doc | `03-user-roles.md` (only when explicitly requested after this lock) |

---

## 1. How to use this backlog

This document is the **single source of truth** for product planning and development tracking.

| Field | Meaning |
| --- | --- |
| **Module** | Product area |
| **Feature** | Named capability |
| **Description** | What the feature delivers |
| **Priority** | Must / Should / Could |
| **Target Version** | V1 / V1.1 / Future |
| **User Roles** | Who uses or is affected |
| **Dependencies** | Other features or external prerequisites |
| **Acceptance Criteria** | Measurable done-when conditions |
| **Status** | Planned (until delivery tracking begins) |

**Conventions**

- Feature IDs (`FEAT-…`) are stable traceability keys into requirements (`FR-…` / `NFR-…`).
- **Assessment System** features are the core domain and take scheduling precedence when conflicts arise.
- No certificates. No institutional tenancy in V1.
- This backlog does **not** include database design, API contracts, UI specs, or code.

---

## 2. Backlog summary

| Module | V1 Must (approx.) | Notes |
| --- | --- | --- |
| Authentication & Accounts | High | Includes academic profile |
| Learning System | High | Hierarchy, editorial, soft delete, M2M |
| Assessment System | Critical | Question Bank, Practice, Exam, Review, Analytics |
| Book Library | High | Multi-format + entitlements |
| Student Dashboard | High | Goals, streak, history |
| Search | Medium | Global, entitlement-aware |
| Blog & CMS | Medium | SEO public content |
| Notifications | Medium | In-app first |
| Subscription & Payments | High | Entitlements V1; gateways phased |
| Administration | High | Bulk ops, audit, preview |
| Reporting & Analytics | Medium | Staff + learner views |
| Settings | Medium | Platform + learner prefs |
| API | Medium | API-first foundation |
| Future Modules | — | AI, mobile, OSCE, institutions, etc. |

---

## 3. Authentication & Accounts

### FEAT-AUTH-01 — User registration

| Field | Value |
| --- | --- |
| Module | Authentication & Accounts |
| Feature | User registration |
| Description | Individual learners can create a Nursilo account. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student (guest → Student) |
| Dependencies | None |
| Acceptance Criteria | A new user can register with required fields; duplicate email is rejected; account is created in Student role by default. |
| Status | Planned |

### FEAT-AUTH-02 — Login and logout

| Field | Value |
| --- | --- |
| Module | Authentication & Accounts |
| Feature | Login and logout |
| Description | Secure session-based authentication for all roles. |
| Priority | Must |
| Target Version | V1 |
| User Roles | All |
| Dependencies | FEAT-AUTH-01 |
| Acceptance Criteria | Valid credentials grant access; logout ends session; failed logins do not reveal whether email exists beyond safe messaging. |
| Status | Planned |

### FEAT-AUTH-03 — Password reset

| Field | Value |
| --- | --- |
| Module | Authentication & Accounts |
| Feature | Password reset |
| Description | Users can reset forgotten passwords via a secure flow. |
| Priority | Must |
| Target Version | V1 |
| User Roles | All authenticated roles |
| Dependencies | FEAT-AUTH-01 |
| Acceptance Criteria | User can request reset, set a new password via valid token/link, and log in with the new password; expired tokens fail. |
| Status | Planned |

### FEAT-AUTH-04 — Basic profile management

| Field | Value |
| --- | --- |
| Module | Authentication & Accounts |
| Feature | Basic profile management |
| Description | Users view and update name, contact, and basic account fields. |
| Priority | Must |
| Target Version | V1 |
| User Roles | All |
| Dependencies | FEAT-AUTH-02 |
| Acceptance Criteria | Authenticated user can view and update allowed profile fields; changes persist across sessions. |
| Status | Planned |

### FEAT-AUTH-05 — Academic profile

| Field | Value |
| --- | --- |
| Module | Authentication & Accounts |
| Feature | Academic profile |
| Description | Learners maintain Academic Program, Institution, Current Semester/Year, optional Expected Graduation Year, and optional Current Study Goal. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-AUTH-04 |
| Acceptance Criteria | Student can save all academic profile fields; optional fields may be empty; values are available for later analytics/personalization use. |
| Status | Planned |

### FEAT-AUTH-06 — Role assignment

| Field | Value |
| --- | --- |
| Module | Authentication & Accounts |
| Feature | Role assignment |
| Description | Platform supports Super Admin, Admin, Editor, Reviewer, Author, and Student roles. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Super Admin, Admin |
| Dependencies | FEAT-AUTH-02; FEAT-ADM-01 |
| Acceptance Criteria | A user can hold an assigned role; role changes are reflected on next privileged action; Students cannot open admin surfaces. |
| Status | Planned |

### FEAT-AUTH-07 — UI language preference

| Field | Value |
| --- | --- |
| Module | Authentication & Accounts |
| Feature | UI language preference (Bangla / English) |
| Description | Learners choose Bangla or English for the interface. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student (and staff as applicable) |
| Dependencies | FEAT-AUTH-02 |
| Acceptance Criteria | Selected language persists for the user; UI strings switch between Bangla and English. |
| Status | Planned |

---

## 4. Learning System

### FEAT-LRN-01 — Content hierarchy

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Content hierarchy |
| Description | Model and manage Course → Subject → Unit → Chapter → Topic → Lesson → Learning Material. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Super Admin, Admin, Editor, Author, Reviewer; Student (consume) |
| Dependencies | FEAT-EDT-01 |
| Acceptance Criteria | Staff can create the full hierarchy; learners only see Published nodes; navigation follows the hierarchy. |
| Status | Planned |

### FEAT-LRN-02 — Reusable composable content

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Reusable composable content |
| Description | Learning objects are shared source-of-truth records composed into multiple contexts without duplication. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Author, Admin |
| Dependencies | FEAT-LRN-01 |
| Acceptance Criteria | The same learning material/question can be linked into multiple valid contexts without creating duplicate source records. |
| Status | Planned |

### FEAT-LRN-03 — Many-to-many academic relationships

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Many-to-many academic relationships |
| Description | Support academically valid M2M links (e.g., question↔topics, lesson↔subjects, book↔courses). |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Author, Admin |
| Dependencies | FEAT-LRN-01; FEAT-QB-02; FEAT-LIB-01 |
| Acceptance Criteria | Staff can associate one question with multiple topics; one lesson with multiple subjects; one book with multiple courses; forced 1:1 is not required. |
| Status | Planned |

### FEAT-LRN-04 — Learner content browsing

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Learner content browsing |
| Description | Students browse and open published learning content per entitlements. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-LRN-01; FEAT-SUB-01 |
| Acceptance Criteria | Published entitled content opens; Draft/Review/Archived content is hidden from Students; premium-only items respect entitlements. |
| Status | Planned |

### FEAT-LRN-05 — Continue Learning

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Continue Learning |
| Description | Resume from the learner’s last learning position. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-LRN-04; FEAT-LRN-06 |
| Acceptance Criteria | After leaving a lesson, returning via Continue Learning opens the last relevant position. |
| Status | Planned |

### FEAT-LRN-06 — Learning progress tracking

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Learning progress tracking |
| Description | Track progress at topic/lesson granularity. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-LRN-04 |
| Acceptance Criteria | Completing or advancing through a lesson updates stored progress visible on dashboard/progress views. |
| Status | Planned |

### FEAT-LRN-07 — Soft delete / archive learning content

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Soft delete / archive learning content |
| Description | Learning materials and hierarchy content are archived/soft-deleted rather than hard-deleted. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Admin, Super Admin |
| Dependencies | FEAT-LRN-01; FEAT-EDT-01 |
| Acceptance Criteria | Archiving removes content from learner discovery but retains records for staff/history; hard delete is not the default path. |
| Status | Planned |

### FEAT-EDT-01 — Editorial workflow

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Editorial workflow |
| Description | Content lifecycle: Draft → Review → Approved → Published → Archived. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Author, Reviewer, Editor, Admin |
| Dependencies | FEAT-AUTH-06 |
| Acceptance Criteria | Each transition is enforceable by role; learners only consume Published; invalid transitions are blocked. |
| Status | Planned |

### FEAT-EDT-02 — Draft authoring

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Draft authoring |
| Description | Authors create and edit Draft learning objects and related content. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Author, Editor, Admin |
| Dependencies | FEAT-EDT-01 |
| Acceptance Criteria | Author can save Draft content invisible to Students; Editor/Admin can edit per permissions. |
| Status | Planned |

### FEAT-EDT-03 — Content review

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Content review |
| Description | Reviewers accept or reject content in Review state. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Reviewer, Editor, Admin |
| Dependencies | FEAT-EDT-02 |
| Acceptance Criteria | Reviewer can move content to Approved or return to Draft with a recorded outcome. |
| Status | Planned |

### FEAT-EDT-04 — Publish and archive

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Publish and archive |
| Description | Editors/Admins publish Approved content and archive Published content. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Admin, Super Admin |
| Dependencies | FEAT-EDT-03 |
| Acceptance Criteria | Publishing makes content learner-visible (if entitled); archiving removes it from active discovery. |
| Status | Planned |

### FEAT-EDT-05 — Unpublished content preview

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Unpublished content preview |
| Description | Editors, Reviewers, and Admins preview content before publish. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Reviewer, Admin |
| Dependencies | FEAT-EDT-02 |
| Acceptance Criteria | Staff can open a preview of Draft/Review/Approved content; Students cannot access that preview URL. |
| Status | Planned |

### FEAT-EDT-06 — Content attribution

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Content attribution |
| Description | Support source/attribution metadata for learning objects and books. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Author, Editor, Admin |
| Dependencies | FEAT-LRN-01; FEAT-LIB-01 |
| Acceptance Criteria | Staff can store attribution fields and view them in admin; published items can expose attribution where policy requires. |
| Status | Planned |

### FEAT-I18N-01 — Multilingual educational content

| Field | Value |
| --- | --- |
| Module | Learning System |
| Feature | Multilingual educational content |
| Description | Bangla and English content representations without duplicating tables per language. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Author, Editor, Student |
| Dependencies | FEAT-LRN-01; FEAT-AUTH-07 |
| Acceptance Criteria | A content item can hold Bangla and/or English fields; missing translation falls back per defined rules without table duplication. |
| Status | Planned |

---

## 5. Assessment System

### 5.1 Question Bank

### FEAT-QB-01 — Question types

| Field | Value |
| --- | --- |
| Module | Assessment System / Question Bank |
| Feature | Question types |
| Description | Support MCQ, True/False, Best Answer, Clinical Scenario Questions, and Image-Based Questions. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Author, Editor, Reviewer, Admin; Student (attempt) |
| Dependencies | FEAT-EDT-01 |
| Acceptance Criteria | Staff can create each type; learners can answer each type in practice/exam flows. |
| Status | Planned |

### FEAT-QB-02 — Question metadata and structure

| Field | Value |
| --- | --- |
| Module | Assessment System / Question Bank |
| Feature | Question metadata and structure |
| Description | Stem, options, correct answer(s), explanation, reference book, difficulty, hierarchy links, language, tags. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Author, Editor, Reviewer, Admin |
| Dependencies | FEAT-QB-01; FEAT-LRN-03 |
| Acceptance Criteria | All listed fields can be stored and edited; difficulty is Easy/Medium/Hard/Expert; language is filterable. |
| Status | Planned |

### FEAT-QB-03 — Question bookmarking

| Field | Value |
| --- | --- |
| Module | Assessment System / Question Bank |
| Feature | Question bookmarking |
| Description | Learners bookmark questions for later review. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-QB-01; FEAT-AUTH-02 |
| Acceptance Criteria | Student can bookmark/unbookmark; bookmarked set is listable in review/dashboard. |
| Status | Planned |

### FEAT-QB-04 — Report question error

| Field | Value |
| --- | --- |
| Module | Assessment System / Question Bank |
| Feature | Report question error |
| Description | Learners report errors on questions; staff triage. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student; Editor, Admin, Reviewer |
| Dependencies | FEAT-QB-01; FEAT-ADM-01 |
| Acceptance Criteria | Student can submit a report; staff can see open reports and mark resolved/dismissed. |
| Status | Planned |

### FEAT-QB-05 — Question versioning for attempt integrity

| Field | Value |
| --- | --- |
| Module | Assessment System / Question Bank |
| Feature | Question versioning for attempt integrity |
| Description | Edits to questions must not change historical exam attempts; versioning or equivalent immutable snapshot strategy. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Author, Editor, Admin; Student (historical review) |
| Dependencies | FEAT-QB-02; FEAT-EXM-04 |
| Acceptance Criteria | After a published question is edited, a prior completed attempt still shows the content/answers as of that attempt. |
| Status | Planned |

### FEAT-QB-06 — Duplicate question detection

| Field | Value |
| --- | --- |
| Module | Assessment System / Question Bank |
| Feature | Duplicate question detection |
| Description | Help authors identify potential duplicate questions during creation. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Author, Editor, Admin |
| Dependencies | FEAT-QB-02 |
| Acceptance Criteria | When creating/editing a question, system surfaces likely duplicates for staff review; staff can proceed or cancel. |
| Status | Planned |

### FEAT-QB-07 — Soft delete questions

| Field | Value |
| --- | --- |
| Module | Assessment System / Question Bank |
| Feature | Soft delete questions |
| Description | Questions are archived/soft-deleted, not permanently destroyed by default. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Admin |
| Dependencies | FEAT-QB-02; FEAT-EDT-01 |
| Acceptance Criteria | Soft-deleted questions leave active pools; historical attempts remain reviewable per FEAT-QB-05. |
| Status | Planned |

### FEAT-QB-08 — Clinical Scenario and Image-Based support

| Field | Value |
| --- | --- |
| Module | Assessment System / Question Bank |
| Feature | Clinical Scenario and Image-Based support |
| Description | Clinical Scenario Questions and Image-Based Questions support case text and associated media. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Author, Editor; Student |
| Dependencies | FEAT-QB-01 |
| Acceptance Criteria | Staff can attach case text/media; learners see them during practice/exam. |
| Status | Planned |

### 5.2 Practice

### FEAT-PRC-01 — Practice by Topic, Chapter, Subject

| Field | Value |
| --- | --- |
| Module | Assessment System / Practice |
| Feature | Practice by Topic, Chapter, Subject |
| Description | Start formative practice scoped to topic, chapter, or subject. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-QB-02; FEAT-SUB-01; FEAT-LRN-01 |
| Acceptance Criteria | Student can start each scope; only published entitled questions are drawn; session records answers. |
| Status | Planned |

### FEAT-PRC-02 — Random practice

| Field | Value |
| --- | --- |
| Module | Assessment System / Practice |
| Feature | Random practice |
| Description | Random question practice within entitlement rules. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-PRC-01 |
| Acceptance Criteria | Random session returns varied entitled questions; free-tier caps apply when configured. |
| Status | Planned |

### FEAT-PRC-03 — Custom practice

| Field | Value |
| --- | --- |
| Module | Assessment System / Practice |
| Feature | Custom practice |
| Description | Build practice from filters (topic, difficulty, count, etc.). |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-PRC-01; FEAT-QB-02 |
| Acceptance Criteria | Student can configure filters and start a session matching those filters within available inventory and entitlements. |
| Status | Planned |

### FEAT-PRC-04 — Free-tier practice limits

| Field | Value |
| --- | --- |
| Module | Assessment System / Practice |
| Feature | Free-tier practice limits |
| Description | Enforce configurable free practice volume. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student; Admin (configure) |
| Dependencies | FEAT-SUB-01; FEAT-SET-01 |
| Acceptance Criteria | Free user hitting the cap is blocked from further free practice until reset/upgrade; premium is not capped by free rules. |
| Status | Planned |

### FEAT-PRC-05 — Practice session recording

| Field | Value |
| --- | --- |
| Module | Assessment System / Practice |
| Feature | Practice session recording |
| Description | Persist answers, correctness, and timing where applicable. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-PRC-01 |
| Acceptance Criteria | Completed practice session stores per-question results retrievable in review/history. |
| Status | Planned |

### 5.3 Exam Engine

### FEAT-EXM-01 — Chapter and subject exams

| Field | Value |
| --- | --- |
| Module | Assessment System / Exam Engine |
| Feature | Chapter and subject exams |
| Description | Structured exams at chapter and subject scope. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-QB-02; FEAT-SUB-01 |
| Acceptance Criteria | Student can start chapter/subject exams; score and status are stored on completion. |
| Status | Planned |

### FEAT-EXM-02 — Timed exams

| Field | Value |
| --- | --- |
| Module | Assessment System / Exam Engine |
| Feature | Timed exams |
| Description | Exams with enforced duration and auto-submit on timeout. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-EXM-01 |
| Acceptance Criteria | Timer is visible; at expiry the attempt submits automatically; late answers after expiry are not accepted. |
| Status | Planned |

### FEAT-EXM-03 — Mock tests

| Field | Value |
| --- | --- |
| Module | Assessment System / Exam Engine |
| Feature | Mock tests |
| Description | Configurable mocks (blueprint, length, timing, entitlement). |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student; Admin/Editor (configure) |
| Dependencies | FEAT-EXM-02; FEAT-SUB-02 |
| Acceptance Criteria | Staff can configure a mock; entitled students can take it; unlimited mocks require premium entitlement. |
| Status | Planned |

### FEAT-EXM-04 — Exam attempt persistence

| Field | Value |
| --- | --- |
| Module | Assessment System / Exam Engine |
| Feature | Exam attempt persistence |
| Description | Persist score, breakdown, completion status; keep completed attempts permanently (subject to future retention policy). |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-EXM-01; FEAT-QB-05 |
| Acceptance Criteria | Completed attempts remain available in exam history for later review; deletion is not available as a casual user action in V1. |
| Status | Planned |

### FEAT-EXM-05 — Premium exam tracks

| Field | Value |
| --- | --- |
| Module | Assessment System / Exam Engine |
| Feature | Premium exam tracks |
| Description | Licensing, Government Job, NCLEX, and Prometric preparation exam sets. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student (Premium) |
| Dependencies | FEAT-SUB-02; FEAT-EXM-03 |
| Acceptance Criteria | Premium user can access each track’s published sets; free user is blocked or limited to configured teasers only. |
| Status | Planned |

### FEAT-EXM-06 — Entitlement enforcement on exams

| Field | Value |
| --- | --- |
| Module | Assessment System / Exam Engine |
| Feature | Entitlement enforcement on exams |
| Description | Prevent exam access bypass via direct URLs or API. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-SUB-03; FEAT-API-01 |
| Acceptance Criteria | Unauthorized start/submit attempts fail server-side with no score credit. |
| Status | Planned |

### FEAT-EXM-07 — Resume interrupted exam

| Field | Value |
| --- | --- |
| Module | Assessment System / Exam Engine |
| Feature | Resume interrupted exam |
| Description | Learners can resume an in-progress exam after disconnect, browser close, or accidental exit, within exam rules. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-EXM-02; FEAT-EXM-04 |
| Acceptance Criteria | An in-progress attempt can be resumed with previously saved answers intact; remaining time (if timed) continues from server-side remaining duration; completed attempts cannot be resumed as new live attempts. |
| Status | Planned |

### FEAT-EXM-08 — Saved custom exam templates

| Field | Value |
| --- | --- |
| Module | Assessment System / Exam Engine |
| Feature | Saved custom exam templates |
| Description | Learners can save custom exam/practice filter configurations as reusable templates. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Student |
| Dependencies | FEAT-PRC-03; FEAT-EXM-01 |
| Acceptance Criteria | Student can save, rename, list, and delete personal templates; starting from a template creates a new attempt using the saved filters within entitlements. |
| Status | Planned |

### 5.4 Review

### FEAT-REV-01 — Wrong-answer review

| Field | Value |
| --- | --- |
| Module | Assessment System / Review |
| Feature | Wrong-answer review |
| Description | Review incorrect answers from past attempts. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-EXM-04; FEAT-PRC-05 |
| Acceptance Criteria | Student can open a list of wrong answers from a selected attempt and see explanation when policy allows. |
| Status | Planned |

### FEAT-REV-02 — Bookmarked question review

| Field | Value |
| --- | --- |
| Module | Assessment System / Review |
| Feature | Bookmarked question review |
| Description | Review bookmarked questions. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-QB-03 |
| Acceptance Criteria | Student can navigate all bookmarked questions and practice/review them. |
| Status | Planned |

### FEAT-REV-03 — Explanation display in review

| Field | Value |
| --- | --- |
| Module | Assessment System / Review |
| Feature | Explanation display in review |
| Description | Show correct answer and detailed explanation per entitlement/policy. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-REV-01; FEAT-SUB-01 |
| Acceptance Criteria | When allowed, review shows correct option and explanation; when not allowed, content is withheld consistently. |
| Status | Planned |

### 5.5 Analytics (Assessment)

### FEAT-ANL-01 — Study progress and exam history analytics

| Field | Value |
| --- | --- |
| Module | Assessment System / Analytics |
| Feature | Study progress and exam history analytics |
| Description | Track and present study progress and exam history per learner. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-LRN-06; FEAT-EXM-04 |
| Acceptance Criteria | Dashboard/history shows progress metrics and past exam attempts with scores/dates. |
| Status | Planned |

### FEAT-ANL-02 — Weak and strong topics

| Field | Value |
| --- | --- |
| Module | Assessment System / Analytics |
| Feature | Weak and strong topics |
| Description | Derive weak/strong topics from attempt data. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-ANL-01; FEAT-PRC-05 |
| Acceptance Criteria | After sufficient attempts, student sees weak and strong topic lists that update as new results arrive. |
| Status | Planned |

### FEAT-ANL-03 — Advanced analytics (premium)

| Field | Value |
| --- | --- |
| Module | Assessment System / Analytics |
| Feature | Advanced analytics (premium) |
| Description | Deeper performance insights gated to premium; basic progress may remain free. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-SUB-02; FEAT-ANL-02 |
| Acceptance Criteria | Free user sees basic progress only; premium user sees advanced analytics surfaces. |
| Status | Planned |

### FEAT-ANL-04 — Chart visualizations

| Field | Value |
| --- | --- |
| Module | Assessment System / Analytics |
| Feature | Chart visualizations |
| Description | Visual analytics on web using Chart.js. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Student |
| Dependencies | FEAT-ANL-01 |
| Acceptance Criteria | At least one progress/performance chart renders with real learner data on the dashboard or analytics page. |
| Status | Planned |

### FEAT-ANL-05 — AI-ready analytics signals

| Field | Value |
| --- | --- |
| Module | Assessment System / Analytics |
| Feature | AI-ready analytics signals |
| Description | Keep attempt/progress data structured for future AI tutor and adaptive learning. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Engineering / future AI modules |
| Dependencies | FEAT-ANL-01 |
| Acceptance Criteria | Attempt-level results retain topic, correctness, timing, and question identity suitable for future adaptive features (no AI product shipped in V1). |
| Status | Planned |

---

## 6. Book Library

### FEAT-LIB-01 — Book catalog metadata

| Field | Value |
| --- | --- |
| Module | Book Library |
| Feature | Book catalog metadata |
| Description | Category, subject, author, edition, publisher, cover image; multi-course linking. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Admin; Student (browse) |
| Dependencies | FEAT-LRN-03; FEAT-EDT-01 |
| Acceptance Criteria | Staff can CRUD metadata; published books appear in catalog with cover and details. |
| Status | Planned |

### FEAT-LIB-02 — Multi-format resources

| Field | Value |
| --- | --- |
| Module | Book Library |
| Feature | Multi-format resources |
| Description | Support PDF, EPUB, HTML articles, and image-based resources. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Admin; Student |
| Dependencies | FEAT-LIB-01 |
| Acceptance Criteria | Each format type can be uploaded/associated and opened by an entitled learner in an appropriate reader view. |
| Status | Planned |

### FEAT-LIB-03 — Online reading

| Field | Value |
| --- | --- |
| Module | Book Library |
| Feature | Online reading |
| Description | Read entitled books/resources online. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-LIB-02; FEAT-SUB-01 |
| Acceptance Criteria | Entitled student can open and read; unentitled access is denied. |
| Status | Planned |

### FEAT-LIB-04 — Premium book gating

| Field | Value |
| --- | --- |
| Module | Book Library |
| Feature | Premium book gating |
| Description | Premium books require premium entitlement. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-SUB-02 |
| Acceptance Criteria | Free user cannot read/download premium books; premium user can. |
| Status | Planned |

### FEAT-LIB-05 — Book bookmarks

| Field | Value |
| --- | --- |
| Module | Book Library |
| Feature | Book bookmarks |
| Description | Bookmark books/reading positions where format allows. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Student |
| Dependencies | FEAT-LIB-03 |
| Acceptance Criteria | Student can save a bookmark and return to that book/position. |
| Status | Planned |

### FEAT-LIB-06 — Entitled downloads

| Field | Value |
| --- | --- |
| Module | Book Library |
| Feature | Entitled downloads |
| Description | Downloads obey entitlement and access permissions. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-LIB-04; FEAT-SUB-03 |
| Acceptance Criteria | Download is allowed only when policy and entitlement permit; otherwise request fails server-side. |
| Status | Planned |

### FEAT-LIB-07 — Soft delete library items

| Field | Value |
| --- | --- |
| Module | Book Library |
| Feature | Soft delete library items |
| Description | Books/resources are archived/soft-deleted by default. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Admin |
| Dependencies | FEAT-LIB-01 |
| Acceptance Criteria | Archived items leave learner catalog but remain recoverable for staff. |
| Status | Planned |

---

## 7. Student Dashboard

### FEAT-DSH-01 — Core dashboard widgets

| Field | Value |
| --- | --- |
| Module | Student Dashboard |
| Feature | Core dashboard widgets |
| Description | Continue Learning, Today’s Goal, Study Progress, Exam History. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-LRN-05; FEAT-ANL-01 |
| Acceptance Criteria | Logged-in student sees each widget with real or empty-state data (not broken placeholders). |
| Status | Planned |

### FEAT-DSH-02 — Performance and library widgets

| Field | Value |
| --- | --- |
| Module | Student Dashboard |
| Feature | Performance and library widgets |
| Description | Weak/Strong Topics, Bookmarks, Saved Notes, Recent Activity. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-ANL-02; FEAT-QB-03; FEAT-DSH-04 |
| Acceptance Criteria | Each section lists user-specific items or a clear empty state. |
| Status | Planned |

### FEAT-DSH-03 — Streak, subscription, notifications summary

| Field | Value |
| --- | --- |
| Module | Student Dashboard |
| Feature | Streak, subscription, notifications summary |
| Description | Show study streak, subscription status, and notifications summary. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-SUB-04; FEAT-NTF-01 |
| Acceptance Criteria | Subscription status matches entitlement service; streak updates with qualifying study activity; unread notification count is visible. |
| Status | Planned |

### FEAT-DSH-04 — Personal notes

| Field | Value |
| --- | --- |
| Module | Student Dashboard |
| Feature | Personal notes |
| Description | Create/edit/delete notes linked to learning objects or questions. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-AUTH-02 |
| Acceptance Criteria | Notes are private to the owner; CRUD works; notes appear in Saved Notes. |
| Status | Planned |

### FEAT-DSH-05 — Today’s Goal

| Field | Value |
| --- | --- |
| Module | Student Dashboard |
| Feature | Today’s Goal |
| Description | Learner sets or tracks a daily study goal. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-DSH-01 |
| Acceptance Criteria | Student can set a daily goal and see progress toward it for the current day. |
| Status | Planned |

---

## 8. Search

### FEAT-SRCH-01 — Global search

| Field | Value |
| --- | --- |
| Module | Search |
| Feature | Global search |
| Description | Search across courses, books, lessons, questions, and authors. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student; staff (as applicable) |
| Dependencies | FEAT-LRN-01; FEAT-LIB-01; FEAT-QB-02 |
| Acceptance Criteria | Query returns ranked/grouped results from all five entity types when matches exist. |
| Status | Planned |

### FEAT-SRCH-02 — Entitlement-aware search

| Field | Value |
| --- | --- |
| Module | Search |
| Feature | Entitlement-aware search |
| Description | Results respect publish state and entitlements; no premium payload leakage beyond allowed teasers. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-SRCH-01; FEAT-SUB-03 |
| Acceptance Criteria | Free user cannot open premium-only full content from search; unpublished items never appear for Students. |
| Status | Planned |

### FEAT-SRCH-03 — Bilingual search competence

| Field | Value |
| --- | --- |
| Module | Search |
| Feature | Bilingual search competence |
| Description | Basic Bangla and English query support. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Student |
| Dependencies | FEAT-SRCH-01; FEAT-I18N-01 |
| Acceptance Criteria | Sample Bangla and English queries return relevant published matches for indexed content. |
| Status | Planned |

---

## 9. Blog & CMS

### FEAT-CMS-01 — Marketing and landing pages

| Field | Value |
| --- | --- |
| Module | Blog & CMS |
| Feature | Marketing and landing pages |
| Description | Manage public marketing/landing pages. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Admin, Editor |
| Dependencies | FEAT-EDT-01 (or CMS publish rules) |
| Acceptance Criteria | Staff can publish a landing page visible to anonymous visitors with correct title/content. |
| Status | Planned |

### FEAT-CMS-02 — Blog

| Field | Value |
| --- | --- |
| Module | Blog & CMS |
| Feature | Blog |
| Description | Create, publish, and publicly read blog posts. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Admin; public visitors |
| Dependencies | FEAT-CMS-01 |
| Acceptance Criteria | Published post has public URL; draft post is not public. |
| Status | Planned |

### FEAT-CMS-03 — SEO for public pages

| Field | Value |
| --- | --- |
| Module | Blog & CMS |
| Feature | SEO for public pages |
| Description | Titles, meta, clean URLs, indexable public content. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Editor, Admin |
| Dependencies | FEAT-CMS-01; FEAT-CMS-02 |
| Acceptance Criteria | Public pages expose title/meta description; authenticated app areas can be marked non-index where appropriate. |
| Status | Planned |

### FEAT-CMS-04 — Contact and feedback

| Field | Value |
| --- | --- |
| Module | Blog & CMS |
| Feature | Contact and feedback |
| Description | Public/authenticated contact and feedback submission for support, content issues, and general inquiries. |
| Priority | Should |
| Target Version | V1 |
| User Roles | Student, public visitors; Admin (triage) |
| Dependencies | FEAT-ADM-01 |
| Acceptance Criteria | User can submit a contact/feedback form with required fields; submission is stored for staff review; spam/abuse basic safeguards exist; submitter receives confirmation of receipt (in-app or on-page). |
| Status | Planned |

---

## 10. Notifications

### FEAT-NTF-01 — In-app notifications

| Field | Value |
| --- | --- |
| Module | Notifications |
| Feature | In-app notifications |
| Description | Notify learners of relevant system/content events. |
| Priority | Should |
| Target Version | V1 |
| User Roles | Student; Admin (emit) |
| Dependencies | FEAT-AUTH-02 |
| Acceptance Criteria | Student receives in-app notification entries; can mark read; dashboard summary reflects unread count. |
| Status | Planned |

### FEAT-NTF-02 — Email notifications

| Field | Value |
| --- | --- |
| Module | Notifications |
| Feature | Email notifications |
| Description | Email for account security and key subscription events. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Student |
| Dependencies | FEAT-AUTH-03; FEAT-SUB-05 |
| Acceptance Criteria | Password reset and successful premium activation emails are delivered when email provider is configured. |
| Status | Planned |

### FEAT-NTF-03 — Announcement system

| Field | Value |
| --- | --- |
| Module | Notifications |
| Feature | Announcement system |
| Description | Platform-wide or targeted announcements from admins to learners (e.g., maintenance, new content, exam campaigns). |
| Priority | Should |
| Target Version | V1 |
| User Roles | Admin, Super Admin; Student (receive) |
| Dependencies | FEAT-NTF-01; FEAT-ADM-01 |
| Acceptance Criteria | Admin can create, publish, and unpublish an announcement; entitled/target learners see it in-app; unpublished announcements are not visible to Students. |
| Status | Planned |

---

## 11. Subscription & Payments

### FEAT-SUB-01 — Central entitlement model

| Field | Value |
| --- | --- |
| Module | Subscription & Payments |
| Feature | Central entitlement model |
| Description | Free vs Premium entitlements enforced in domain services. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student; Admin |
| Dependencies | FEAT-AUTH-02 |
| Acceptance Criteria | A single entitlement check governs practice caps, bank access, mocks, premium books, and advanced analytics consistently. |
| Status | Planned |

### FEAT-SUB-02 — Premium unlock package

| Field | Value |
| --- | --- |
| Module | Subscription & Payments |
| Feature | Premium unlock package |
| Description | Premium unlocks complete question bank, unlimited mocks, licensing/govt/NCLEX/Prometric tracks, premium books/notes, advanced analytics. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-SUB-01 |
| Acceptance Criteria | Premium-flagged account passes all premium capability checks listed; free account fails them (except configured teasers). |
| Status | Planned |

### FEAT-SUB-03 — Subscription status on dashboard

| Field | Value |
| --- | --- |
| Module | Subscription & Payments |
| Feature | Subscription status on dashboard |
| Description | Show current plan/status to the learner. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-SUB-01; FEAT-DSH-03 |
| Acceptance Criteria | Dashboard status matches Free or Premium (and expiry if applicable). |
| Status | Planned |

### FEAT-SUB-04 — Payment gateways (bKash, Nagad, SSLCommerz)

| Field | Value |
| --- | --- |
| Module | Subscription & Payments |
| Feature | Payment gateways (bKash, Nagad, SSLCommerz) |
| Description | Bangladesh-first checkout when payments are enabled. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-SUB-01; external merchant accounts |
| Acceptance Criteria | Student can initiate checkout via at least one configured gateway; successful paid order activates premium only after verified confirmation. |
| Status | Planned |

### FEAT-SUB-05 — Payment verification and idempotency

| Field | Value |
| --- | --- |
| Module | Subscription & Payments |
| Feature | Payment verification and idempotency |
| Description | Verify callbacks/webhooks; prevent duplicate entitlement grants. |
| Priority | Must |
| Target Version | V1 |
| User Roles | System; Admin |
| Dependencies | FEAT-SUB-04; FEAT-ADM-03 |
| Acceptance Criteria | Forged/unverified callbacks do not grant premium; duplicate confirmed events do not double-extend incorrectly. |
| Status | Planned |

### FEAT-SUB-06 — Manual premium grant

| Field | Value |
| --- | --- |
| Module | Subscription & Payments |
| Feature | Manual premium grant |
| Description | Admins can grant/revoke premium for support operations. |
| Priority | Should |
| Target Version | V1 |
| User Roles | Super Admin, Admin |
| Dependencies | FEAT-SUB-01; FEAT-ADM-03 |
| Acceptance Criteria | Admin grant immediately reflects in entitlement checks; action is audit-logged. |
| Status | Planned |

---

## 12. Administration

### FEAT-ADM-01 — Admin console coverage

| Field | Value |
| --- | --- |
| Module | Administration |
| Feature | Admin console coverage |
| Description | Manage users, roles, learning hierarchy, books, question bank, exams, mocks, blog, CMS, notifications, subscriptions, payments, settings, analytics, logs. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Super Admin, Admin (scoped); Editor/Reviewer/Author per least privilege |
| Dependencies | FEAT-AUTH-06 |
| Acceptance Criteria | Each listed domain has an admin management entry point appropriate to role permissions. |
| Status | Planned |

### FEAT-ADM-02 — Least-privilege staff access

| Field | Value |
| --- | --- |
| Module | Administration |
| Feature | Least-privilege staff access |
| Description | Role capabilities follow least privilege (detailed in user-roles doc). |
| Priority | Must |
| Target Version | V1 |
| User Roles | All staff roles |
| Dependencies | FEAT-AUTH-06 |
| Acceptance Criteria | Author cannot perform Super Admin actions; Student cannot access admin URLs; unauthorized actions fail server-side. |
| Status | Planned |

### FEAT-ADM-03 — Audit logging

| Field | Value |
| --- | --- |
| Module | Administration |
| Feature | Audit logging |
| Description | Log login events, role changes, content publication, question edits, subscription changes, payment events, and other critical admin actions. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Super Admin, Admin |
| Dependencies | FEAT-AUTH-02; FEAT-EDT-04; FEAT-SUB-04 |
| Acceptance Criteria | Each listed event type produces an auditable record with actor, timestamp, and action summary retrievable in admin logs. |
| Status | Planned |

### FEAT-ADM-04 — Bulk import/export

| Field | Value |
| --- | --- |
| Module | Administration |
| Feature | Bulk import/export |
| Description | Structured bulk import/export for questions, learning materials, and books. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Admin, Editor (as permitted) |
| Dependencies | FEAT-QB-02; FEAT-LRN-01; FEAT-LIB-01 |
| Acceptance Criteria | Staff can export a sample set and re-import without corrupting required fields; validation errors are reported per row/item. |
| Status | Planned |

### FEAT-ADM-05 — Soft delete policy in admin

| Field | Value |
| --- | --- |
| Module | Administration |
| Feature | Soft delete policy in admin |
| Description | Admin delete actions for important content default to archive/soft delete. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Admin, Editor |
| Dependencies | FEAT-LRN-07; FEAT-QB-07; FEAT-LIB-07 |
| Acceptance Criteria | Delete/archive controls soft-delete learning materials, books, and questions; hard delete is not the primary UX. |
| Status | Planned |

---

## 13. Reporting & Analytics

### FEAT-RPT-01 — Learner performance reports (self)

| Field | Value |
| --- | --- |
| Module | Reporting & Analytics |
| Feature | Learner performance reports (self) |
| Description | Student-facing performance summaries beyond raw history. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Student |
| Dependencies | FEAT-ANL-01; FEAT-ANL-03 |
| Acceptance Criteria | Student can open a report view showing accuracy trends by topic for a selected period. |
| Status | Planned |

### FEAT-RPT-02 — Admin content and usage overview

| Field | Value |
| --- | --- |
| Module | Reporting & Analytics |
| Feature | Admin content and usage overview |
| Description | High-level counts for users, content, attempts, and subscriptions. |
| Priority | Should |
| Target Version | V1 |
| User Roles | Super Admin, Admin |
| Dependencies | FEAT-ADM-01 |
| Acceptance Criteria | Admin overview shows current totals for users, published questions, attempts (period), and premium subscribers. |
| Status | Planned |

### FEAT-RPT-03 — Question error report queue metrics

| Field | Value |
| --- | --- |
| Module | Reporting & Analytics |
| Feature | Question error report queue metrics |
| Description | Visibility into open vs resolved question error reports. |
| Priority | Could |
| Target Version | V1.1 |
| User Roles | Editor, Admin |
| Dependencies | FEAT-QB-04 |
| Acceptance Criteria | Staff can see counts of open/resolved reports and filter the queue. |
| Status | Planned |

### FEAT-RPT-04 — Content performance analytics (admin)

| Field | Value |
| --- | --- |
| Module | Reporting & Analytics |
| Feature | Content performance analytics for administrators |
| Description | Admin-facing analytics on how courses, topics, lessons, and books perform (engagement, completion, and related usage). |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Super Admin, Admin, Editor |
| Dependencies | FEAT-LRN-06; FEAT-ANL-01; FEAT-ADM-01 |
| Acceptance Criteria | Admin can view performance summaries for selected content nodes (e.g., views/starts, completions, or equivalent engagement metrics available from V1 data). |
| Status | Planned |

### FEAT-RPT-05 — Question usage statistics

| Field | Value |
| --- | --- |
| Module | Reporting & Analytics |
| Feature | Question usage statistics |
| Description | Per-question attempt count, accuracy rate, and difficulty trend for content quality monitoring. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Super Admin, Admin, Editor, Author |
| Dependencies | FEAT-PRC-05; FEAT-EXM-04; FEAT-QB-02 |
| Acceptance Criteria | Staff can open a question’s usage view showing attempt count, accuracy rate, and a difficulty/accuracy trend over a selectable period. |
| Status | Planned |

---

## 14. Settings

### FEAT-SET-01 — Platform settings

| Field | Value |
| --- | --- |
| Module | Settings |
| Feature | Platform settings |
| Description | Configure freemium caps, site identity, and feature toggles without code changes. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Super Admin, Admin |
| Dependencies | FEAT-SUB-01; FEAT-PRC-04 |
| Acceptance Criteria | Changing free practice cap in settings changes enforcement for free users without redeploying application code. |
| Status | Planned |

### FEAT-SET-02 — Learner preferences

| Field | Value |
| --- | --- |
| Module | Settings |
| Feature | Learner preferences |
| Description | Language and basic notification preferences. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Student |
| Dependencies | FEAT-AUTH-07; FEAT-NTF-01 |
| Acceptance Criteria | Preference changes persist and affect UI language / notification behavior. |
| Status | Planned |

---

## 15. API

### FEAT-API-01 — Domain services API-first foundation

| Field | Value |
| --- | --- |
| Module | API |
| Feature | Domain services API-first foundation |
| Description | Business rules for entitlements, attempts, and content access live in reusable services usable by web and future clients. |
| Priority | Must |
| Target Version | V1 |
| User Roles | Engineering; future Flutter clients |
| Dependencies | FEAT-SUB-01; FEAT-EXM-06 |
| Acceptance Criteria | Critical entitlement and attempt operations are invocable via service layer (not template-only logic); web UI uses the same rules. |
| Status | Planned |

### FEAT-API-02 — Versioned public/mobile API surface

| Field | Value |
| --- | --- |
| Module | API |
| Feature | Versioned public/mobile API surface |
| Description | Stable DRF API suitable for future Flutter apps. |
| Priority | Should |
| Target Version | V1.1 |
| User Roles | Future mobile clients |
| Dependencies | FEAT-API-01 |
| Acceptance Criteria | Documented API version exists for auth, content browse, practice/exam start-submit, and entitlement status. |
| Status | Planned |

---

## 16. Future Modules

### FEAT-FUT-01 — AI tutor

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | AI tutor |
| Description | AI-assisted explanations and tutoring grounded in Assessment System data. |
| Priority | Could |
| Target Version | Future |
| User Roles | Student |
| Dependencies | FEAT-ANL-05; FEAT-API-01 |
| Acceptance Criteria | (Future) Tutor can explain a missed question using stored attempt context without changing historical attempt integrity. |
| Status | Planned |

### FEAT-FUT-02 — Adaptive learning

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Adaptive learning |
| Description | Practice recommendations adapt to weak topics and difficulty. |
| Priority | Could |
| Target Version | Future |
| User Roles | Student |
| Dependencies | FEAT-ANL-02; FEAT-ANL-05 |
| Acceptance Criteria | (Future) System proposes next practice set biased toward weak topics with measurable personalization. |
| Status | Planned |

### FEAT-FUT-03 — Clinical case simulation mode

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Clinical case simulation mode |
| Description | Dedicated multi-step clinical simulation experiences beyond Clinical Scenario Questions. |
| Priority | Could |
| Target Version | Future |
| User Roles | Student |
| Dependencies | FEAT-QB-08 |
| Acceptance Criteria | (Future) Learner can complete a multi-step simulation with scored outcomes. |
| Status | Planned |

### FEAT-FUT-04 — Centralized media library

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Centralized media library |
| Description | Shared anatomy diagrams and medical assets reusable across lessons, questions, and books. |
| Priority | Should |
| Target Version | Future |
| User Roles | Author, Editor |
| Dependencies | FEAT-LRN-02 |
| Acceptance Criteria | (Future) One media asset can be reused in multiple questions/lessons without re-upload duplication. |
| Status | Planned |

### FEAT-FUT-05 — OSCE and nursing procedures

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | OSCE and nursing procedures |
| Description | OSCE prep and nursing procedures learning modules. |
| Priority | Could |
| Target Version | Future |
| User Roles | Student |
| Dependencies | FEAT-LRN-01 |
| Acceptance Criteria | (Future) Published OSCE/procedure modules are browsable and completable by entitled learners. |
| Status | Planned |

### FEAT-FUT-06 — Flashcards

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Flashcards |
| Description | Spaced study flashcards linked to topics. |
| Priority | Could |
| Target Version | Future |
| User Roles | Student |
| Dependencies | FEAT-LRN-01 |
| Acceptance Criteria | (Future) Student can review topic-linked flashcard decks and track known/unknown cards. |
| Status | Planned |

### FEAT-FUT-07 — Medical calculators

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Medical calculators |
| Description | Clinical/study calculators for nursing practice. |
| Priority | Could |
| Target Version | Future |
| User Roles | Student |
| Dependencies | None |
| Acceptance Criteria | (Future) At least one calculator produces correct results for a defined validation set. |
| Status | Planned |

### FEAT-FUT-08 — Flutter mobile apps

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Flutter mobile apps |
| Description | Android/iOS clients on the API-first backend. |
| Priority | Should |
| Target Version | Future |
| User Roles | Student |
| Dependencies | FEAT-API-02 |
| Acceptance Criteria | (Future) Student can register/login, practice, and complete an exam on mobile using the same entitlements as web. |
| Status | Planned |

### FEAT-FUT-09 — PWA / offline features

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | PWA / offline features |
| Description | Progressive Web App and offline study capabilities (premium foreshadowed). |
| Priority | Could |
| Target Version | Future |
| User Roles | Student |
| Dependencies | FEAT-SUB-02; FEAT-API-01 |
| Acceptance Criteria | (Future) Entitled user can access a defined offline subset and sync results when online. |
| Status | Planned |

### FEAT-FUT-10 — Institutional plans

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Institutional plans |
| Description | College/hospital/coaching seat licensing after product-market fit. |
| Priority | Could |
| Target Version | Future |
| User Roles | Institution admin; Student |
| Dependencies | FEAT-SUB-01; product-market fit |
| Acceptance Criteria | (Future) Institution can provision seats; member students inherit institutional entitlements. |
| Status | Planned |

### FEAT-FUT-11 — International payments

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | International payments |
| Description | Add international payment providers after local gateways. |
| Priority | Could |
| Target Version | Future |
| User Roles | Student |
| Dependencies | FEAT-SUB-04 |
| Acceptance Criteria | (Future) At least one international provider successfully activates premium after verified payment. |
| Status | Planned |

### FEAT-FUT-12 — Data retention policy tooling

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Data retention policy tooling |
| Description | Controlled retention/removal workflows for historical attempts per policy. |
| Priority | Could |
| Target Version | Future |
| User Roles | Super Admin |
| Dependencies | FEAT-EXM-04 |
| Acceptance Criteria | (Future) Retention job can archive/remove attempts only according to an approved policy with audit trail. |
| Status | Planned |

### FEAT-FUT-13 — Question discussion

| Field | Value |
| --- | --- |
| Module | Future Modules |
| Feature | Question discussion |
| Description | Learner discussion threads on questions (clarifications, peer discussion) with moderation. |
| Priority | Could |
| Target Version | Future |
| User Roles | Student; Moderator/Admin |
| Dependencies | FEAT-QB-02; FEAT-AUTH-02 |
| Acceptance Criteria | (Future) Entitled student can post/view discussion on a question; staff can moderate/hide posts; discussions do not alter scored attempt records. |
| Status | Planned |

---

## 17. Explicit non-features (do not schedule)

| Item | Rule |
| --- | --- |
| Course certificates / certificate module | Forbidden in V1 and not on Future backlog as a product goal |
| Institutional tenancy in V1 | Deferred to FEAT-FUT-10 only |

---

## 18. Suggested V1 delivery waves (planning aid)

| Wave | Focus | Example feature IDs |
| --- | --- | --- |
| Wave A | Accounts, roles, settings, entitlements skeleton | FEAT-AUTH-*, FEAT-SUB-01, FEAT-SET-01, FEAT-API-01 |
| Wave B | Learning hierarchy + editorial + i18n | FEAT-LRN-*, FEAT-EDT-*, FEAT-I18N-01 |
| Wave C | Question Bank core + soft delete + versioning | FEAT-QB-* |
| Wave D | Practice + Exam + Review | FEAT-PRC-*, FEAT-EXM-*, FEAT-REV-* |
| Wave E | Analytics + dashboard | FEAT-ANL-*, FEAT-DSH-* |
| Wave F | Library + search + CMS/SEO | FEAT-LIB-*, FEAT-SRCH-*, FEAT-CMS-* |
| Wave G | Payments + audit + bulk import | FEAT-SUB-04/05, FEAT-ADM-03/04, FEAT-NTF-* |

Waves are guidance only; detailed sequencing belongs in `04-development-roadmap.md`.

---

## 19. Document Lock

**Status:** `docs/02-feature-list.md` is **Approved** and locked at **Version 1.0.0**.

Additional backlog items incorporated without restructuring:

- FEAT-EXM-07 — Resume interrupted exam (Must, V1)
- FEAT-EXM-08 — Saved custom exam templates (Should, V1.1)
- FEAT-FUT-13 — Question discussion (Could, Future)
- FEAT-RPT-04 — Content performance analytics for administrators (Should, V1.1)
- FEAT-RPT-05 — Question usage statistics (Should, V1.1)
- FEAT-NTF-03 — Announcement system (Should, V1)
- FEAT-CMS-04 — Contact and feedback (Should, V1)

Proceed to `docs/03-user-roles.md` **only when explicitly requested**. No code and no additional documentation will be produced until then.

---

*Nursilo — Learn. Practice. Succeed.*
