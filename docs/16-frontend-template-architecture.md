# Nursilo — Frontend Template Architecture

| Field | Value |
| --- | --- |
| Document | `16-frontend-template-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`15`](15-frontend-page-architecture.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative conceptual Django template architecture for Nursilo V1 |
| Out of scope | Actual Django template source; HTML; CSS; Tailwind; JavaScript; Alpine; HTMX; Python; APIs; database implementation; Figma; source code |
| Nature | **Additive only** — does not modify locked docs `00`–`15` |

---

## 1. Purpose

Nursilo requires a dedicated **template architecture** so page compositions from [`15`](15-frontend-page-architecture.md) map predictably into the Django-template layer—without embedding business logic or prescribing source syntax.

| Layer | Authority |
| --- | --- |
| [`12`](12-design-system.md) | Visual language |
| [`13`](13-frontend-architecture.md) | Frontend technology & boundaries |
| [`14`](14-frontend-component-architecture.md) | Reusable components |
| [`15`](15-frontend-page-architecture.md) | Complete page composition |
| **This document** | Conceptual Django-template organization & contracts |
| Future implementation | Actual templates / partials / fragments |

```text
12 Design System
    ↓
13 Frontend Architecture
    ↓
14 Component Architecture
    ↓
15 Page Architecture
    ↓
16 Template Architecture
    ↓
Future implementation
```

Goals: predictable organization; controlled inheritance; reusable partials; clean page composition; component integration; accessibility and localization safety; security-safe rendering; explicit HTMX fragment boundaries; minimal duplication.

This document maps architectural concepts to the Django-template layer. It does **not** prescribe actual source syntax.

---

## 2. Template Architecture Principles

| Principle | Meaning |
| --- | --- |
| Server-rendered first | Templates deliver primary HTML from the server |
| Reuse before duplication | Prefer existing layouts, partials, components |
| Explicit inheritance | Clear parent → child layout chain |
| Small focused partials | One responsibility per fragment |
| Components remain reusable | Not page-bound |
| Pages remain composition-focused | Assemble sections; don’t invent shells |
| Templates remain presentation-only | No domain/service logic |
| No business logic | No rules engines in templates |
| No repository access | No persistence queries |
| No authorization / entitlement / scoring / payment truth | Server decides; templates display |
| Server-provided context is authoritative | Render what the presentation boundary supplies |
| Accessibility by default | Semantics, labels, focus |
| Localization-safe | Bangla / English expansion |
| Responsive-safe | Mobile-first composition |
| HTMX boundaries explicit | Fragments for approved partial updates only |
| Alpine behavior remains local | Temporary UI only |
| Avoid deep nesting & giant templates | Keep composition shallow and readable |
| Avoid duplicate markup patterns | One pattern per concern |

---

## 3. Template Hierarchy

Conceptual hierarchy:

```text
Root
→ Base Layouts
→ Family Layouts
→ Page Templates
→ Sections
→ Components
→ HTMX Fragments
```

| Level | Role |
| --- | --- |
| **Root / Global Base** | Document shell, shared head region, global landmarks |
| **Family Layout** | Public, Auth, Student, Staff, Assessment, Reader, Error chrome |
| **Page Template** | One page purpose; maps to docs/15 |
| **Section** | Related content grouping |
| **Component** | Reusable UI unit from docs/14 |
| **HTMX Fragment** | Partial response for progressive updates |

Example family tree (conceptual names only):

```text
Base
→ Public Layout
→ Auth Layout
→ Student Layout
→ Staff Layout
→ Assessment Layout
→ Reader Layout
→ Error Layout

Student Layout
→ Dashboard Page
→ Learning Page
→ Practice Page
→ Library Page
→ Subscription Page

Assessment Layout
→ Practice Session
→ Exam Session
→ Result Pages
```

No actual template syntax.

---

## 4. Base Template Architecture

| Base | Owns | Must not own |
| --- | --- | --- |
| **Global base** | Document structure; page metadata region; accessibility landmarks; global feedback region; language context; shared footer hooks | Domain workflows; RBAC calculation |
| **Public base** | Marketing chrome; SEO-friendly structure; public nav | Authenticated app chrome (unless explicitly required) |
| **Auth base** | Focused identity shell; form-centric landmarks | Student/staff navigation |
| **Student base** | Student nav; notification entry; subscription state presentation where appropriate | Staff modules; exam focus chrome |
| **Staff base** | Dense operational chrome; role-scoped module nav | Learner marketing chrome |
| **Assessment base** | Reduced chrome; timer/progress regions; exit-protection presentation | Unrelated portal widgets |
| **Reader base** | Minimal chrome; content-first shell | Catalog-heavy chrome |
| **Error / system base** | Simple recovery shell; clear next-action region | Sensitive internals |

Prevent unrelated concerns from entering the base layout.

---

## 5. Layout Inheritance Model

```text
Global Base
    ↓
Family Layout
    ↓
Page Template
    ↓
Section Composition
    ↓
Reusable Components
```

| Rule |
| --- |
| Inheritance should be shallow |
| Family layouts hold family-specific structure only |
| Pages must not duplicate the global shell |
| Components must not own page layout |
| No circular inheritance |
| No layout-specific business logic |

---

## 6. Public Template Architecture

Conceptual templates: Home; About; Pricing; Blog index; Blog post; Contact; Course marketing; Legal.

Priorities: SEO; accessibility; branding; responsive composition; clear CTA; CMS content; trustworthy premium messaging.

No authenticated application chrome unless explicitly required.

---

## 7. Authentication Template Architecture

Conceptual templates: Register; Login; Verify email; Resend verification; Forgot password; Reset password; Logout confirmation; Re-authentication; Password change.

Rules: focused layout; consistent form components; localized validation; security-safe messaging; no sensitive leakage; clear session/authentication states.

---

## 8. Student Template Architecture

Conceptual page templates: Student dashboard; Learning; Practice; Exams; Library; Search; Notifications; Subscription; Profile; Security; Settings.

Each maps to [`15`](15-frontend-page-architecture.md). Student templates consume server-provided presentation data only.

---

## 9. Learning Template Architecture

Conceptual templates: Course list; Course overview; Subject; Unit; Chapter; Topic; Lesson; Learning material; Progress.

Hierarchy:

```text
Course → Subject → Unit → Chapter → Topic → Lesson → Material
```

Reusable boundaries: breadcrumbs; progress; lesson navigation; continue learning; completion; locked; empty; error.

---

## 10. Assessment Template Architecture

Conceptual templates: Practice setup; Practice session; Practice result; Exam catalog; Exam detail; Exam start; Exam session; Submission confirmation; Exam result; Review; Attempt history.

Regions:

```text
Assessment Layout
→ Assessment Header
→ Progress/Timer Region
→ Question Region
→ Navigation Region
→ Action Region
→ Result/Review Region
```

| Critical rule |
| --- |
| Templates only **render** server-provided attempt, timer, question version, answer, submission, score, and completion state |
| Templates must **never calculate** these |

---

## 11. Library Template Architecture

Conceptual templates: Library catalog; Search/filter results; Book detail; Reader; Downloads; Bookmarks.

Reader priorities: content; readable width; minimal chrome; navigation; bookmark state; access state.

Storage access remains outside templates.

---

## 12. Subscription / Billing Template Architecture

Conceptual templates: Pricing; Plan comparison; Current subscription; Upgrade; Checkout; Pending payment; Payment result; Billing summary.

Templates render payment state supplied by the server. Never optimistic “success” from browser state alone. Never expose sensitive payment information.

---

## 13. Staff / Admin Template Architecture

Conceptual templates: Staff dashboard; Admin dashboard; Users; Roles; Editorial queue; Review queue; Question bank; Exam management; Library management; CMS; Announcements; Subscriptions/payments; Reports; Audit logs; Settings.

Templates receive role-aware presentation data. They do **not** calculate RBAC.

---

## 14. CMS / Editorial Template Architecture

Conceptual templates: Content list; Draft workspace; Review queue; Preview; Approval; Publishing; Archive; History/revision presentation.

Use only approved workflow states from [`09`](09-business-rules.md). No new workflow authority.

---

## 15. Component-to-Template Mapping

| Component (docs/14) | Template representation |
| --- | --- |
| Button | Action control presentation |
| FormField | Field presentation |
| DataTable | Staff/admin table presentation |
| QuestionOption | Assessment option presentation |
| BookCard | Library catalog item presentation |
| NotificationItem | Notification list item presentation |
| ExamTimer | Assessment timer presentation |
| Alert | Feedback presentation |

Components remain reusable across pages.

---

## 16. Partial / Fragment Architecture

Conceptual categories: navigation; form; feedback; data rows; list items; table; modal content; assessment; notification; library; dashboard sections.

| Rule |
| --- |
| One clear responsibility |
| Safely reusable |
| No hidden business logic |
| Support progressive enhancement |
| Avoid undocumented parent-state requirements |

---

## 17. HTMX Fragment Boundary

| Appropriate for | Not authority for |
| --- | --- |
| Filtering; search; pagination | Authorization / RBAC |
| Bookmark state; notification read state | Entitlement |
| Inline form updates; modal content | Scoring |
| Staff queue refresh; small dashboard updates | Payment confirmation; session validation; business rules |

Server response determines final rendered state. Do not generate HTMX attributes in this document.

---

## 18. Alpine Template Boundary

| Compatible regions | Must never own |
| --- | --- |
| Dropdowns; tabs; disclosures | Authorization; entitlement |
| Modal visibility; password visibility | Scoring; payment truth |
| Temporary UI state; visual countdown display | Session truth; persistence |
| Local interaction preferences | Business rules |

Do not generate Alpine source in this document.

---

## 19. Template Context / Data Contract

Conceptual context categories: page metadata; navigation; user display data; role-aware visibility; entitlement state; content; progress; assessment state; notification state; form state; validation messages; localized labels; URLs/actions; accessibility metadata.

Templates must not obtain data from repositories. Presentation data is prepared by the presentation/application boundary.

---

## 20. Template State Architecture

Conceptual representations: default; loading; empty; success; validation error; business conflict; permission denied; entitlement denied; session expired; server error; maintenance; offline/best-effort; selected; expanded/collapsed; locked; Free; Premium; Pending; Completed; Failed.

Not every template requires every state.

---

## 21. Accessibility Template Contract

Template-level responsibilities: semantic structure; heading hierarchy; landmarks; accessible labels; form associations; error identification; status communication; keyboard support; focus regions; modal semantics; screen-reader announcements; reduced-motion compatibility; zoom/text resizing.

Follow [`11`](11-ui-ux-specification.md), [`12`](12-design-system.md), [`14`](14-frontend-component-architecture.md), and [`15`](15-frontend-page-architecture.md).

---

## 22. Localization Template Contract

Support Bangla; English; mixed-language content; long labels; text expansion; localized dates/numbers/currency; medical terminology; localized validation/errors.

Do not hard-code language assumptions into template architecture.

---

## 23. Security-Aware Rendering

Safe handling for: authentication state; session expiry; permission denial; entitlement denial; suspended accounts; email verification; re-authentication; security notifications; sensitive account actions.

| Never expose |
| --- |
| Passwords; tokens; session identifiers |
| Internal filesystem paths |
| Private payment information; secrets |
| Unpublished protected content |

Templates are never a security boundary.

---

## 24. Responsive Template Architecture

| Viewport | Behavior |
| --- | --- |
| Mobile | Stacked sections; compact navigation; touch-friendly controls |
| Tablet | Adaptive composition; comfortable reading; assessment usable |
| Desktop | Wider learning layouts; dense staff/admin structures |
| Large desktop | Extra space without excessive content width |
| Assessment | Focus layout remains usable |
| Reader | Content remains primary |

---

## 25. Template Naming Conventions

Names describe domain, page purpose, and component/partial purpose.

| Good conceptual names | Avoid |
| --- | --- |
| base, public, student, staff, assessment, reader, dashboard, course, lesson, practice, exam, book, subscription, notification, form-field, question-option, data-table, empty-state, error-state | random, misc, temp, thing, box, widget1, page2, final-final |

Names must remain stable and predictable.

---

## 26. Template Directory Organization

Conceptual organization only (not a command to create directories now):

```text
templates/
    base/
    layouts/
    public/
    auth/
    student/
    learning/
    assessment/
    library/
    subscription/
    notifications/
    staff/
    admin/
    cms/
    components/
    partials/
    errors/
```

---

## 27. Template Dependency Rules

Allowed conceptual direction:

```text
Page Template → Family Layout → Section/Pattern → Component → Primitive
```

| Rule |
| --- |
| Lower-level templates remain reusable |
| Primitives remain domain-neutral |
| Components must not depend on page templates |
| Partials must not create circular dependencies |
| Assessment components must not depend on billing templates |
| Public components must not require authenticated page context |
| Shared components avoid unnecessary domain coupling |

---

## 28. Template Reuse Rules

Before creating a template/partial:

1. Search existing template vocabulary.  
2. Check whether an existing template can compose the requirement.  
3. Extend only when semantics remain coherent.  
4. Create a new partial only when reuse improves clarity.  
5. Avoid duplicate visual/structural implementations.  
6. Remove obsolete templates when safely deprecated.  

---

## 29. Template Business-Logic Boundary

| Templates may | Templates must not |
| --- | --- |
| Present values | Query repositories |
| Iterate already-authorized display collections | Mutate persistence |
| Render server-provided state | Calculate permissions/entitlements |
| Present validation messages | Score assessments / verify payments |
| Display conditional presentation states | Determine session validity |
| Expose approved navigation/actions | Implement workflow transitions / make security decisions |

Simple presentation conditionals are acceptable when they do not duplicate business rules.

---

## 30. Design System Alignment

All templates must represent [`12`](12-design-system.md) consistently: typography; semantic colors; spacing; surfaces; borders; elevation; iconography; feedback; status; motion; accessibility; premium presentation.

No template may introduce an independent visual language.

---

## 31. Page Architecture Alignment

Every page template must map to [`15`](15-frontend-page-architecture.md).

| Page | Conceptual mapping |
| --- | --- |
| Student Dashboard | Student Layout → Dashboard Page → Dashboard Sections → Reusable Components |
| Exam Session | Assessment Layout → Exam Session Page → Exam Sections → Assessment Components |
| Book Reader | Reader Layout → Reader Page → Reader Sections → Library Components |

No page should bypass the approved page architecture.

---

## 32. Template Testing Strategy

Conceptual tests: rendering; correct inheritance; component composition; accessibility; localization; responsive states; loading/empty/error; permission; entitlement; authentication; assessment state; HTMX fragment behavior; Alpine enhancement behavior; regression.

Complement: component tests; page tests; service/domain tests; integration tests.

---

## 33. Template Performance

Avoid excessive nesting; avoid redundant rendering; avoid unnecessary repeated data structures; use fragments appropriately; paginate large datasets; keep assessment rendering lightweight; avoid oversized media; minimize client enhancement; avoid unnecessary partial requests.

Correctness and security remain higher priority than optimization.

---

## 34. Template Documentation

Each future implemented template family should conceptually document: purpose; parent layout; expected context; child sections; reusable components; supported states; accessibility; localization; HTMX behavior if applicable; Alpine behavior if applicable; security considerations; known limitations.

Do not create implementation documentation files now.

---

## 35. Future Template Extensions

**Future-only:** Flutter equivalents; component/template bridge for future clients; dark mode; AI Tutor; Adaptive Learning; Offline Mode; Institution Portal; advanced visualization.

Must not silently become V1 requirements.

---

## 36. Template Governance

Template ownership; architecture review; UX review; design-system review; accessibility review; security review; duplicate prevention; breaking changes; deprecation; technical debt; naming consistency.

New template families require justification.

---

## 37. Cross References

| Document | Use |
| --- | --- |
| [`03`](03-user-roles.md) | Role-aware presentation |
| [`04`](04-system-architecture.md) | Adapter → services |
| [`05`](05-domain-model.md) | Domain hierarchy |
| [`07`](07-security-and-session-management.md) | Auth/security rendering |
| [`08`](08-api-design.md) | Future clients |
| [`09`](09-business-rules.md) | Workflow & entitlements |
| [`10`](10-development-roadmap.md) | Delivery scope |
| [`11`](11-ui-ux-specification.md) | Experience contracts |
| [`12`](12-design-system.md) | Visual system |
| [`13`](13-frontend-architecture.md) | Tech boundaries |
| [`14`](14-frontend-component-architecture.md) | Component vocabulary |
| [`15`](15-frontend-page-architecture.md) | Page composition |

**This document does not modify any approved document.**

---

## 38. Acceptance Criteria

This document is acceptable when:

1. Template architecture principles and hierarchy are defined  
2. Base layouts and layout inheritance are defined  
3. Public, authentication, student, learning, assessment, library, subscription/payment, staff/admin, and CMS/editorial templates are defined  
4. Component-to-template mapping and partial/fragment architecture are defined  
5. HTMX and Alpine boundaries are defined  
6. Context/data contracts and template state architecture are defined  
7. Accessibility, localization, security-aware rendering, and responsive behavior are defined  
8. Naming conventions and conceptual directory organization are defined  
9. Dependency, reuse, and business-logic boundaries are defined  
10. Design-system and page-architecture alignment are defined  
11. Testing, performance, documentation, and governance are defined  
12. Future extensions are explicitly Future-only  
13. **No** actual Django template syntax is generated  
14. **No** HTML/CSS/JS/HTMX/Alpine/Python source is generated  
15. **No** API/database implementation is generated  
16. Docs `00`–`15` remain unchanged  

---

## 39. Document Lock

**Status:** `docs/16-frontend-template-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual Django template architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`15` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*
