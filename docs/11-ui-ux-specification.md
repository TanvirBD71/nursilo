# Nursilo — UI/UX Specification

| Field | Value |
| --- | --- |
| Document | `11-ui-ux-specification.md` |
| Version | `1.0.0` |
| Status | **Approved** — LOCKED — authoritative V1 UI/UX specification |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`10`](10-development-roadmap.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative UI/UX specification for Nursilo Version 1 |
| Out of scope | HTML; CSS; Tailwind; JavaScript; HTMX; Alpine.js; Django templates; Figma files; component implementation; source code; API implementation |
| Nature | **Additive only** — does not modify locked docs `00`–`10` |

---

## 1. Purpose

This document defines **how users experience Nursilo**—not how the interface is implemented.

It is the UX authority for designers and developers. It establishes:

- Information architecture and navigation  
- User journeys and page inventory  
- Layout expectations for public, student, and staff surfaces  
- Accessibility, localization, and responsive behavior  
- Interaction patterns and assessment/library/admin experiences  

It does **not** prescribe markup, stylesheets, scripts, template code, or design-tool files. Implementation must follow this specification and the approved business rules ([`09`](09-business-rules.md)), security UX constraints ([`07`](07-security-and-session-management.md)), and product backlog ([`02`](02-feature-list.md)).

---

## 2. UX Principles

| Principle | Meaning for Nursilo |
| --- | --- |
| **Simplicity** | Prefer clear primary actions; avoid cluttered dashboards and competing CTAs |
| **Consistency** | Same patterns for forms, exams, lists, and feedback across the product |
| **Accessibility** | Usable with keyboard, assistive tech, and readable contrast |
| **Learnability** | New nursing students can start practice without training manuals |
| **Discoverability** | Core paths (Continue Learning, Practice, Exams, Library) are obvious |
| **Performance perception** | Interfaces feel responsive with clear loading and progress feedback |
| **Mobile-first thinking** | Primary learner flows complete comfortably on phones |
| **Progressive disclosure** | Advanced filters/analytics appear when needed, not all at once |
| **Minimal cognitive load** | One job per screen/section where practical |
| **Bangladesh-first design** | Bangla/English parity, local payment UX, culturally clear educational tone |

---

## 3. Design Philosophy

Nursilo should feel:

| Trait | UX implication |
| --- | --- |
| **Professional** | Credible for exams and career prep—not playful gimmicks |
| **Educational** | Content and practice hierarchy are always clear |
| **Modern** | Clean layout, purposeful motion, contemporary typography hierarchy (implementation later) |
| **Minimal** | Prefer open structure over card-heavy chrome where interaction does not require containment |
| **Trustworthy** | Security notices, entitlements, and pricing are honest and visible |
| **Accessible** | Inclusive by default |
| **Calm visual hierarchy** | Brand and primary task lead; secondary metadata stays quiet |

Brand signals (name **Nursilo**, tagline **Learn. Practice. Succeed.**) should be strong on public marketing surfaces without overwhelming in-app study focus.

---

## 4. Information Architecture

```text
Public Website
 ├── Home / Marketing
 ├── About / Trust
 ├── Pricing / Premium overview
 ├── Blog
 ├── Contact / Feedback
 └── Legal (as needed)

Authentication
 ├── Register
 ├── Login
 ├── Email verification
 ├── Password reset
 └── Logout

Student Portal
 ├── Dashboard
 ├── Learning (courses → lessons)
 ├── Assessment (practice, exams, review, bookmarks)
 ├── Library
 ├── Search
 ├── Notifications
 ├── Subscription / Billing
 ├── Profile / Academic profile
 ├── Security (devices, login history)
 └── Settings (language, preferences)

Admin / Staff Portals (role-scoped)
 ├── Admin overview
 ├── Users & roles
 ├── Editorial / content hierarchy
 ├── Question Bank
 ├── Exams / mocks
 ├── Library management
 ├── CMS / blog
 ├── Announcements / notifications
 ├── Subscriptions / payments
 ├── Reports / analytics
 ├── Audit logs
 └── Platform settings (Super Admin–bounded)

Shared system
 ├── Error pages
 └── Maintenance
```

Certificates are not part of IA. Institutional portals are Future-only.

---

## 5. Navigation

### 5.1 Public navigation

| Element | Content |
| --- | --- |
| Primary | Home, Courses/Learning overview, Library teaser, Pricing, Blog, Contact |
| CTA | Register / Login / Go Premium |
| Footer | Trust links, legal, language switch, contact |

### 5.2 Student navigation

| Element | Content |
| --- | --- |
| Primary | Dashboard, Learn, Practice, Exams, Library, Search |
| Secondary | Notifications, Subscription, Profile, Security, Settings |
| Persistent utility | Language switch, subscription badge (Free/Premium), notification indicator |

### 5.3 Admin / staff navigation

| Element | Content |
| --- | --- |
| Role-scoped sidebar or equivalent | Only modules permitted by RBAC |
| Examples | Editorial queue, Question Bank, Users, Reports, Settings |
| Escape hatch | Clear return to student view if dual-hat accounts exist (rare) |

### 5.4 Cross-cutting navigation patterns

| Pattern | UX rule |
| --- | --- |
| **Breadcrumbs** | Show hierarchy location in Learning and Admin content trees |
| **Search** | Global entry from student (and staff where useful) chrome |
| **Sidebar** | Preferred for staff dense tools; student may use top nav + optional section nav |
| **Top navigation** | Public + student primary destinations |
| **Footer** | Public and light student footer; minimal in focused exam mode |

**Exam focus mode:** During live timed exams, chrome is reduced (no distracting marketing nav); exit/submit controls remain clear.

---

## 6. User Journeys

| Journey | High-level steps |
| --- | --- |
| **Registration** | Landing → Register → Verify email → Optional academic profile → Dashboard |
| **Login** | Login → Session policy applied → Dashboard (or resume intended deep link) |
| **Purchase Premium** | Pricing/Subscription → Re-auth if required → Checkout → Pending → Confirmed → Entitlement visible |
| **Continue Learning** | Dashboard → Continue Learning → Lesson/material → Progress updates |
| **Practice** | Practice entry → Scope/filters → Session → Answer → Results/review teaser |
| **Take Exam** | Exam list → Start (entitlement check) → Timed/untimed flow → Submit/auto-submit → Results |
| **Review** | Review hub → Wrong answers or bookmarks → Explanation when allowed |
| **Read Book** | Library → Book detail → Entitlement gate → Reader / download if allowed |
| **Search** | Query → Grouped results → Open entitled published item |
| **Profile management** | Profile → Edit basic/academic fields → Save confirmation |
| **Logout** | Choose current / selected / all other / all devices → Confirmed signed-out state |
| **Device security** | Security page → Device list → Revoke → Optional re-auth for sensitive actions |

Journeys must fail closed with clear messages when entitlements, verification, or publish rules block progress.

---

## 7. Page Inventory

### 7.1 Public pages

Home, About, Pricing, Blog index/post, Contact, marketing course teasers (if any), legal.

### 7.2 Authentication pages

Register, Login, Verify email, Resend verification, Forgot password, Reset password, Logout confirmation.

### 7.3 Dashboard pages

Student dashboard; role dashboards for Admin, Editor, Reviewer, Author (scoped).

### 7.4 Learning pages

Course list, subject/unit/chapter/topic navigators, lesson view, learning material view, progress overview.

### 7.5 Assessment pages

Practice setup, practice session, practice result; exam catalog, exam session (focus mode), exam result; review wrong answers; bookmarks; attempt history.

### 7.6 Library pages

Catalog, book detail, reader, downloads (when allowed), library bookmarks (when available).

### 7.7 Subscription pages

Plan status, upgrade/checkout, payment pending/result, billing history summary (as available).

### 7.8 CMS pages

Managed public pages and blog experiences (learner/public facing).

### 7.9 Admin pages

Users/roles, editorial queues, hierarchy CRUD, question bank, exams/mocks, library admin, CMS admin, announcements, subscriptions/payments ops, reports, audit logs, settings (bounded).

### 7.10 Error / system pages

404, 403, 500, maintenance, offline-friendly message (best-effort), validation-centric form states (inline, not only full pages).

---

## 8. Dashboard Specification

### 8.1 Student Dashboard

Must surface (per product requirements):

| Widget / area |
| --- |
| Continue Learning |
| Today’s Goal |
| Study Progress |
| Exam History |
| Weak Topics / Strong Topics (per entitlement) |
| Bookmarks |
| Saved Notes |
| Recent Activity |
| Study Streak |
| Subscription Status |
| Notifications summary |

Layout priority: Continue Learning and today’s study action first; analytics secondary.

### 8.2 Admin Dashboard

Operational overview: users, content counts, attempts (period), premium subscribers, open error reports, payment health summaries (as permitted).

### 8.3 Editor Dashboard

Publishing pipeline: items awaiting publish, recently published, archive candidates, content performance entry points.

### 8.4 Reviewer Dashboard

Review queue: submitted items, approve/reject actions, preview entry.

### 8.5 Author Dashboard

Drafts, returned items, submission status, duplicate-detection warnings when available.

Staff dashboards show **only** RBAC-permitted modules.

---

## 9. Forms & Validation

| Concern | UX rule |
| --- | --- |
| **Input behavior** | Clear labels; required fields marked; sensible defaults |
| **Validation** | Client hints may assist; server validation is authoritative |
| **Inline feedback** | Field-level errors adjacent to inputs |
| **Error messaging** | Localized, non-technical, no secrets/stack traces |
| **Success messaging** | Confirm saves and critical actions |
| **Confirmation dialogs** | Required for destructive or irreversible actions (logout all devices, archive publish, submit exam) |
| **Sensitive actions** | Re-authentication challenges presented clearly when policy requires |

---

## 10. Responsive Design

| Viewport class | Expectation |
| --- | --- |
| **Mobile** | Complete practice, exam, review, continue-learning, and checkout-critical flows |
| **Tablet** | Comfortable reading and exam taking; adaptive nav |
| **Laptop / Desktop** | Full admin density; multi-column learning where helpful |
| **Orientation** | Portrait primary for mobile study; landscape supported without broken exam chrome |

Touch targets must be adequately sized. Tables in admin should offer horizontal scroll or responsive alternatives on small screens.

---

## 11. Accessibility

| Area | Requirement |
| --- | --- |
| **WCAG principles** | Aim for WCAG 2.x AA-oriented practices for V1 learner flows |
| **Keyboard navigation** | All primary actions reachable; visible focus |
| **Focus management** | Modals/dialogs trap focus appropriately; return focus on close |
| **Color contrast** | Text/icons meet contrast expectations; status never by color alone |
| **Screen readers** | Meaningful names/labels; exam timers announced considerately |
| **Touch targets** | Comfortable minimum sizes on mobile |
| **Language switching** | Switcher accessible and persistent |

Accessibility applies to public, student, and staff surfaces (staff may be denser but not inaccessible).

---

## 12. Localization UX

| Concern | UX rule |
| --- | --- |
| **Bangla / English** | Full UI language switch; content falls back per policy when a locale is missing |
| **RTL** | **Not required** for V1 |
| **Dates / numbers** | Locale-appropriate formatting |
| **Search** | Accept Bangla and English queries; empty states explain language coverage honestly |
| **Mixed content** | Avoid layout breakage when Bangla and English strings differ in length |

---

## 13. Visual Consistency

Conceptual design system (no CSS tokens here):

| Element | Consistency rule |
| --- | --- |
| **Typography hierarchy** | Clear H1–H3 / body / meta roles; exam stem highly readable |
| **Spacing system** | Predictable rhythm; dense admin vs airy study modes |
| **Iconography** | Simple, educational metaphors; not emoji-driven |
| **Cards** | Use when they aid interaction/grouping; avoid decorative card spam in heroes |
| **Buttons** | Primary / secondary / danger / quiet hierarchy |
| **Forms** | Shared field, error, help-text patterns |
| **Tables** | Staff lists with sort/filter affordances |
| **Badges** | Free/Premium, difficulty, editorial state, notification unread |
| **Alerts** | Info / success / warning / error |
| **Modals** | Confirmations and focused tasks; not general navigation |

Premium indicators must be honest—never dark-pattern pressure.

---

## 14. Interaction Patterns

| State | UX expectation |
| --- | --- |
| **Loading** | Immediate feedback for navigations and submits |
| **Skeleton screens** | Preferred for dashboard/catalog loading perception |
| **Empty states** | Explain next action (e.g., “Start your first practice”) |
| **Error states** | Recoverable actions when possible |
| **Success states** | Brief confirmation; don’t block flow unnecessarily |
| **Confirmation flows** | Explicit for exam submit, logout-all, archive, payment |
| **Progress indicators** | Lesson progress, today’s goal, exam timer, upload/import progress (staff) |

---

## 15. Search Experience

| Element | V1 / Future |
| --- | --- |
| **Global search** | V1 — courses, books, lessons, questions, authors |
| **Grouped results** | V1 |
| **Filters / sorting** | V1 basic where useful |
| **Entitlement-aware display** | V1 — teasers vs full access clear |
| **Autocomplete** | Future |
| **Recent searches** | Future |

Unpublished/archived learner hits never appear.

---

## 16. Assessment UX

### 16.1 Practice flow

Select scope → optional filters → start → answer questions → see interim/end feedback per policy → review entry.

### 16.2 Exam flow

Select exam → entitlement gate → focus mode → answer → navigate questions → submit or auto-submit → results.

### 16.3 Timer behavior

| Rule |
| --- |
| Timer visible and calm (not panic-inducing) |
| Server time authoritative; client display is indicative |
| Warning as time nears end |
| Auto-submit on expiry with clear post-state |

### 16.4 Resume

Clear “Resume exam” entry when InProgress exists; show remaining time; block resume of Completed.

### 16.5 Question navigation

Flag/review later optional; position indicator; prevent accidental exit without confirm during live exam.

### 16.6 Submission confirmation

Confirm intent; then immutable completed state messaging.

### 16.7 Review flow

Wrong-answer lists, bookmark lists, explanation panels when allowed; version integrity transparent only as needed (no confusing “content changed” scares—history shows what was answered).

---

## 17. Library UX

| Element | UX rule |
| --- | --- |
| **Browsing** | Catalog with metadata, cover, premium badge |
| **Reading** | Online reader for entitled formats |
| **Downloads** | Only when permitted; clear deny state for Free users on premium |
| **Bookmarks** | When available, easy return |
| **Premium indicators** | Visible before paywall friction |

---

## 18. Notification UX

| Element | UX rule |
| --- | --- |
| **In-app** | Bell/indicator + list; read/unread |
| **Announcements** | Distinct from personal notifications when helpful |
| **Priority** | Critical security items elevated |
| **Security notifications** | Clear, non-alarmist, actionable (e.g., review devices) |
| **Secrets** | Never show tokens/passwords in notification bodies |

---

## 19. Admin UX

| Area | UX rule |
| --- | --- |
| **Editorial workflow** | State visible; legal transitions only; preview before publish |
| **Review queue** | Prioritized list; approve/reject with reason |
| **Publishing** | Explicit publish action; confirmation |
| **Audit visibility** | Searchable logs for permitted roles; append-only presentation |
| **User management** | Role assignment with warnings on privilege |
| **Reports** | Simple charts/tables; export later as maturity allows |
| **Bulk import** | Progress + per-row error reporting UX |
| **Least privilege** | Hide inaccessible modules entirely |

---

## 20. Error UX

| Error | User experience |
| --- | --- |
| **404** | Helpful not found + links home/search |
| **403** | Permission denied; no unpublished leakage |
| **500** | Apologetic generic failure; no stack traces |
| **Offline** | Best-effort connectivity message |
| **Maintenance** | Clear maintenance mode messaging |
| **Validation** | Inline field errors |
| **Authentication** | Login required / session expired with re-auth path |
| **Authorization / entitlement** | Upgrade or request access messaging without dark patterns |

---

## 21. Performance UX

| Technique | Intent |
| --- | --- |
| Fast perceived loading | Prioritize above-the-fold study actions |
| Lazy loading (conceptual) | Defer non-critical below-fold content |
| Skeleton screens | Reduce blank-page anxiety |
| Optimistic feedback | Only where safe (e.g., bookmark toggle); never for payments/exam submit |

Exam submit and payment confirmation must feel definitive and wait for server truth.

---

## 22. Future UX

| Surface | Note |
| --- | --- |
| Flutter | Match web mental models; shared journeys |
| AI Tutor | Assistive panel; never rewrite history silently |
| Adaptive Learning | Recommendations as suggestions, not forced paths |
| Offline Mode | Clear sync/offline indicators |
| Institution Portal | Separate IA later; not V1 nav |

---

## 23. Cross References

| Document | UX relevance |
| --- | --- |
| [`00`](00-project-vision.md)–[`02`](02-feature-list.md) | Brand, features, freemium honesty |
| [`03`](03-user-roles.md) | What each role may see |
| [`07`](07-security-and-session-management.md) | Device, session, re-auth, security notification UX |
| [`09`](09-business-rules.md) | Entitlement and workflow gates reflected in UI states |
| [`10`](10-development-roadmap.md) | What ships in MVP vs later |

This specification does **not** modify docs `00`–`10`.

---

## 24. Acceptance Criteria

This document is acceptable when:

1. Complete information architecture exists  
2. User journeys are documented  
3. Navigation is defined for public, student, and staff  
4. Responsive behavior is defined  
5. Accessibility requirements exist  
6. Localization UX is documented (Bangla/English; RTL not required)  
7. Interaction patterns are documented  
8. Assessment UX (practice, exam, timer, resume, review) is defined  
9. Admin UX is defined  
10. **No** HTML, CSS, JavaScript, HTMX, Alpine, Tailwind, Django templates, Figma, or implementation artifacts exist  
11. Locked documents `00`–`10` remain unmodified  

---

## 25. Document Lock

**Status:** `docs/11-ui-ux-specification.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative V1 UI/UX specification. Substantive content remains unchanged. Locked documents `docs/00`–`docs/10` remain unmodified. Next documentation proceeds only when explicitly requested. No implementation artifacts will be generated until separately requested.

---

*Nursilo — Learn. Practice. Succeed.*
