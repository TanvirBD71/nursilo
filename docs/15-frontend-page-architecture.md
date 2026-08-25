# Nursilo — Frontend Page Architecture

| Field | Value |
| --- | --- |
| Document | `15-frontend-page-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`14`](14-frontend-component-architecture.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative page-level frontend architecture for Nursilo V1 |
| Out of scope | Actual HTML; CSS; Tailwind; JavaScript; Alpine; HTMX; Django templates; Python; APIs; database implementation; Figma; source code |
| Nature | **Additive only** — does not modify locked docs `00`–`14` |

---

## 1. Purpose

Nursilo needs **page-level architecture** so complete experiences are assembled consistently from layouts, sections, patterns, and reusable components.

| Layer | Answers |
| --- | --- |
| [`14`](14-frontend-component-architecture.md) | What reusable pieces exist? |
| **This document** | How are those pieces assembled into complete experiences? |

```text
12 Design System
    ↓
13 Frontend Architecture
    ↓
14 Frontend Component Architecture
    ↓
15 Frontend Page Architecture
    ↓
Future implementation
```

Goals: consistent composition, predictable layout selection, page-family consistency, reusable sections, clear page-level states, accessibility and localization safety, and separation of page composition from business logic.

---

## 2. Page Architecture Principles

| Principle | Meaning |
| --- | --- |
| Compose, don't duplicate | Reuse layouts, patterns, components |
| One dominant user goal per page | Clear primary action/purpose |
| Clear hierarchy | Title → primary → secondary |
| Server truth | Pages display server-provided state |
| Components remain reusable | Page-specific logic stays at page/section level |
| Pages do not contain business logic | No scoring/RBAC/entitlement decisions |
| Layouts establish structural context | Shell + nav chrome |
| Sections organize related tasks | Group related UI |
| Progressive disclosure | Advanced details on demand |
| Mobile-first | Learner flows work on phones |
| Accessibility by default | Landmarks, headings, focus |
| Localization-safe | Bangla/English expansion |
| Entitlement-aware presentation | Display Free/Premium/Locked honestly |
| RBAC-aware presentation | Hide only what server permits |
| State-complete pages | Loading/empty/error/permission states |
| Minimal client behavior | HTMX/Alpine enhance only |
| Consistency with docs/11–14 | No rogue patterns |

---

## 3. Page Composition Model

```text
Page
 ↓
Layout
 ↓
Page Header
 ↓
Primary Section(s)
 ↓
Content Pattern(s)
 ↓
Reusable Components
 ↓
Server-provided state/data
```

| Level | Responsibility |
| --- | --- |
| **Page** | Page-level purpose and composition |
| **Layout** | Structural shell and navigation context |
| **Section** | Related content grouping |
| **Pattern** | Recurring interaction/layout solution |
| **Component** | Reusable UI presentation/behavior |

No level may become a hidden business-logic layer.

---

## 4. Page Family Taxonomy

| Family | Purpose | Primary user | Dominant action | Layout | Nav context | Density | Key states | A11y / Responsive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A. Public / Marketing** | Attract & inform | Guest | Register / Premium CTA | Public | Marketing | Airy | Loading, empty CMS | SEO headings; mobile-first |
| **B. Authentication** | Identity | Guest/user | Submit credentials | Auth | Minimal | Focused | Validation, lockout | Strong form a11y |
| **C. Student Dashboard** | Orient study | Student | Continue Learning | Student | Full student | Medium | Empty, returning, Free/Premium | Widget order; stack on mobile |
| **D. Learning** | Consume hierarchy | Student | Open lesson | Student | Breadcrumbs | Calm | Progress, locked | Reading measure |
| **E. Assessment** | Practice/exam | Student | Answer / submit | Focus for live | Reduced chrome | Focused | In progress, result | Timer/focus careful |
| **F. Library** | Read books | Student | Read / download | Student / Reader | Library | Calm/immersive | Locked premium | Reader mobile |
| **G. Subscription / Billing** | Plan & pay | Student | Upgrade / pay | Student | Subscription | Clear | Pending/success/fail | Honest CTAs |
| **H. Profile / Security / Settings** | Account control | User | Save / revoke | Student | Settings | Clear | Re-auth, devices | Security clarity |
| **I. Notifications** | Alerts | User | Open / mark read | Student | Notifications | Medium | Empty, unread | Priority labels |
| **J. Staff** | Content ops | Author/Reviewer/Editor | Review / edit | Staff | Role-scoped | Dense | Queues | Dense but a11y |
| **K. Admin** | Platform ops | Admin/Super Admin | Manage | Staff | Admin modules | Dense | Ops alerts | Tables responsive |
| **L. CMS / Editorial** | Publish content | Staff | Publish | Staff | Editorial | Medium-dense | Workflow states | Preview a11y |
| **M. Error / System** | Recover | Anyone | Go home / retry | Error | Minimal | Simple | 403/404/500 | Clear next action |

---

## 5. Public Page Architecture

Pages: Home, About, Pricing, Blog index, Blog post, Contact, course/learning marketing, Legal.

Rules: strong Nursilo branding; clear primary CTA; SEO-friendly structure; trustworthy premium messaging; accessible navigation; no unnecessary app chrome; responsive marketing layouts.

---

## 6. Authentication Page Architecture

Pages: Register, Login, Email verification, Resend verification, Forgot password, Reset password, Logout confirmation, Re-authentication, Password change.

Rules: focused layout; minimal distraction; clear localized errors; security-safe feedback; no secret leakage; accessible forms.

---

## 7. Student Dashboard Architecture

Hierarchy (visual priority from docs/11–12):

```text
Dashboard
→ Continue Learning
→ Today's Goal
→ Primary Study Action
→ Progress
→ Exam History
→ Weak/Strong Topics
→ Bookmarks
→ Notes
→ Activity
→ Streak
→ Subscription
→ Notifications
```

States: first-visit; active-learning; empty; returning learner; Free/Premium variations; loading; error; mobile stacked composition.

---

## 8. Learning Page Architecture

Pages: Course list, Course overview, Subject, Unit, Chapter, Topic, Lesson, Learning material, Progress.

Hierarchy:

```text
Course → Subject → Unit → Chapter → Topic → Lesson → Learning Material
```

Define: breadcrumbs; progress presentation; navigation context; Continue Learning relationship; completion; unavailable/locked; empty; error.

---

## 9. Practice Page Architecture

Flow:

```text
Practice entry → Practice setup → Practice session → Practice result → Review
```

Composition covers: scope selection; filters; question area; progress; answer state; feedback; result summary; review entry.

Server remains authoritative.

---

## 10. Exam Page Architecture

Flow:

```text
Exam catalog → Exam detail → Start confirmation → Live exam → Submission confirmation → Result → Review
```

Live exam uses: focus layout; reduced chrome; clear timer; question navigation; answer area; submit control; exit protection.

| Server owns | Attempt state; timer; submission; scoring; question version; completion |
| --- | --- |

The page only represents server truth.

---

## 11. Library Page Architecture

Pages: Catalog; Search/filter results; Book detail; Reader; Downloads; Bookmarks.

Reader:

```text
Reader shell → Reader navigation/toolbar → Content region → Reading state → Bookmark/action region
```

Rules: immersive reading; minimal chrome; entitlement-aware access; honest premium states; no unauthorized file-access assumptions.

---

## 12. Subscription / Billing Page Architecture

Pages: Pricing; Plan comparison; Current subscription; Upgrade; Checkout; Payment pending; Payment success; Payment failure; Billing summary.

Payment states come from server truth. No optimistic “payment successful.” No fake urgency or manipulative premium UX.

---

## 13. Profile / Security / Settings Page Architecture

Pages: Profile; Academic profile; Security; Devices; Login history; Password change; Re-authentication; Language; Preferences.

Security pages prioritize clarity and safe actions. Sensitive actions follow [`07`](07-security-and-session-management.md).

---

## 14. Notification Page Architecture

Pages: Notification center; Announcement view; Security notification view; Read/unread; Empty.

Separate personal notifications from announcements when useful. Never expose secrets.

---

## 15. Staff Page Architecture

Structures: Staff dashboard; Editorial queue; Review queue; Author workspace; Reviewer workspace; Content management; Question bank; Exam management; Library management; Reports.

Dense layouts allowed; accessibility required.

---

## 16. Admin Page Architecture

Pages: Admin overview; Users; Roles; Content hierarchy; Question bank; Exams/mocks; Library; CMS; Announcements; Subscriptions/payments; Reports; Audit logs; Settings.

RBAC controls available modules. Frontend never becomes authorization authority.

---

## 17. CMS / Editorial Page Architecture

Pages: Content list; Draft editor workspace; Review queue; Preview; Approval; Publishing; Archive; Revision/history view.

Reflect legal workflow transitions from [`09`](09-business-rules.md). Do not invent new editorial states.

---

## 18. Error / System Page Architecture

Pages: 404; 403; 500; Maintenance; Session expired; Offline/best-effort; Generic failure; Validation failure.

Each provides: clear explanation; appropriate next action; no sensitive information; accessible structure.

---

## 19. Page-Level State Model

Conceptual states: Initial; Loading; Loaded; Empty; Partial; Validation error; Permission denied; Entitlement denied; Session expired; Business conflict; Server error; Maintenance; Offline/best-effort.

| Family | Especially expected states |
| --- | --- |
| Auth | Validation, lockout messaging |
| Dashboard / Learning / Library | Empty, loading, entitlement denied |
| Assessment | In-progress, completed, conflict (non-resumable) |
| Billing | Pending, success, failure |
| Staff/Admin | Empty queues, permission denied |
| Error/System | Matching error type |

---

## 20. Page Data Boundary

Pages may consume: content data; user display data; navigation data; permission-aware visibility; entitlement state; progress; assessment state; notification state; localized labels; URLs/actions.

Pages must **not**: query repositories; implement business rules; calculate authorization/entitlement/scores; access persistence directly.

---

## 21. Page Navigation Relationships

```text
Public → Authentication → Student Portal

Student:
Dashboard ↔ Learn ↔ Practice ↔ Exams ↔ Library ↔ Search
         ↔ Notifications ↔ Subscription ↔ Profile ↔ Security ↔ Settings

Staff/Admin:
Dashboard → Role-scoped operational modules

Assessment:
Catalog → Setup → Session → Result → Review

Learning:
Course → Subject → Unit → Chapter → Topic → Lesson → Material

Library:
Catalog → Book → Reader
```

---

## 22. Page Transition Principles

| Prefer | When |
| --- | --- |
| Full navigation | Major IA changes; auth; exam start/end focus |
| Partial update | Filters, pagination, read state, bookmarks |
| Modal / drawer | Confirmations, focused secondary tasks |
| Inline state update | Small non-navigational changes |

Exam start/end need clear transitions. Payment completion waits for server truth.

---

## 23. Responsive Page Architecture

| Viewport | Behavior |
| --- | --- |
| Mobile | Single-column; accessible nav; touch-friendly assessment; readable lessons; checkout completable |
| Tablet | Comfortable reading; adaptive nav; assessment usable |
| Desktop | Wider learning where justified; staff density |
| Large desktop | Extra space without harming reading measure |

---

## 24. Accessibility Page Contract

Every page conceptually defines: page title; heading hierarchy; landmarks; keyboard route; focus entry/exit; error identification; status communication; accessible navigation; reduced-motion compatibility; zoom/text resizing.

Exam pages require careful focus and timer communication.

---

## 25. Localization Page Contract

Support Bangla, English, mixed-language content, text expansion, localized dates/numbers/currency, medical terminology, long nav labels, localized errors.

No fixed-width assumptions based on English text.

---

## 26. SEO / Public Page Architecture

Conceptual SEO for public pages: meaningful titles; clear content hierarchy; indexable public content where appropriate; canonical conceptual ownership; structured hierarchy; accessible navigation; no indexing of private learner/staff pages.

Do not define metadata code or framework configuration.

---

## 27. Performance Page Architecture

Server-rendered first paint; prioritize critical content; minimize JS; avoid excessive nesting; lazy-load non-critical media where appropriate; paginate large staff lists; keep exam pages lightweight; avoid unnecessary requests.

Correctness and security outrank optimization.

---

## 28. Security / Entitlement Page Boundary

Page-level treatment for: unauthorized page; unavailable feature; premium-only content; suspended account; unverified account; expired session; sensitive action requiring re-authentication.

| Rule |
| --- |
| Server decides access |
| Frontend presents server result |
| No leakage of protected content |
| No security decisions in client code |

---

## 29. Page Composition Rules

1. Every page has one primary purpose.  
2. Use the appropriate layout family.  
3. Reuse existing components.  
4. Reuse existing patterns before creating new ones.  
5. Keep page-specific logic out of components where possible.  
6. Keep business logic outside pages.  
7. Avoid giant pages.  
8. Avoid unnecessary nested sections.  
9. Maintain accessibility hierarchy.  
10. Preserve responsive behavior.  
11. Preserve localization safety.  
12. Preserve entitlement/RBAC presentation truth.  

---

## 30. Page Naming Conventions

Names communicate user-facing purpose, domain, and page family.

| Good | Avoid |
| --- | --- |
| StudentDashboard, CourseOverview, LessonView, PracticeSetup, PracticeSession, ExamCatalog, ExamSession, ExamResult, BookDetail, BookReader, SubscriptionStatus, SecurityDevices, EditorialQueue | Home2, BigDashboard, GreenPage, ExamFinalFinal, TestPage |

---

## 31. Page-to-Component Mapping

Conceptual only:

**Student Dashboard:** Layout → Page Header → Continue Learning → Goal Section → Progress Pattern → Activity Pattern → Subscription Status → Notifications  

**Exam Session:** Exam Layout → Exam Header → Timer → Question Area → Answer Group → Question Navigator → Submit Action  

**Book Reader:** Reader Layout → Reader Header → Reader Toolbar → Content Region → Bookmark/Action Controls  

**Admin Question Bank:** Staff Layout → Page Header → Search/Filter → Data Table → Pagination → Bulk Actions  

No implementation code.

---

## 32. Page Testing Strategy

Conceptual tests: correct layout; navigation; component composition; accessibility; keyboard; responsive; localization; loading/empty/error; permission; entitlement; authentication; assessment states; regression.

Page tests complement component and domain/service tests.

---

## 33. Page Governance

Page ownership; UX review; design-system review; accessibility review; security review; regression review; breaking changes; deprecation; duplicate page prevention.

New pages require justification.

---

## 34. Future Page Extensions

**Future-only:** Flutter page equivalents; Institution Portal; AI Tutor; Adaptive Learning; Offline Mode; advanced analytics; advanced visualization; dark mode–specific page variants.

Must not silently become V1 requirements.

---

## 35. Cross References

| Document | Use |
| --- | --- |
| [`03`](03-user-roles.md) | RBAC presentation |
| [`04`](04-system-architecture.md) | Adapter → services |
| [`05`](05-domain-model.md) | Hierarchy |
| [`07`](07-security-and-session-management.md) | Security pages |
| [`08`](08-api-design.md) | Future clients |
| [`09`](09-business-rules.md) | Workflow & entitlements |
| [`10`](10-development-roadmap.md) | Delivery scope |
| [`11`](11-ui-ux-specification.md) | Experience |
| [`12`](12-design-system.md) | Visual system |
| [`13`](13-frontend-architecture.md) | Tech boundaries |
| [`14`](14-frontend-component-architecture.md) | Component vocabulary |

**This document does not modify any approved document.**

---

## 36. Acceptance Criteria

This document is acceptable when:

1. Page architecture principles and composition hierarchy are defined  
2. Page families are defined  
3. Public, authentication, student dashboard, learning, practice, exam, library, subscription/billing, profile/security/settings, notification, staff, admin, CMS/editorial, and error/system pages are defined  
4. Page-level state model and data boundaries are defined  
5. Navigation relationships and transition principles are defined  
6. Responsive, accessibility, localization, SEO (conceptual), and performance architectures are defined  
7. Security/entitlement boundaries and composition/naming rules are defined  
8. Page-to-component mappings, testing, governance, and Future-only extensions are defined  
9. **No** HTML/CSS/JS/HTMX/Alpine/Django template/source code is generated  
10. **No** API/database implementation is generated  
11. Docs `00`–`14` remain unchanged  

---

## 37. Document Lock

**Status:** `docs/15-frontend-page-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative page-level frontend architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`14` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*
