# Nursilo — Frontend Component Architecture

| Field | Value |
| --- | --- |
| Document | `14-frontend-component-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`13`](13-frontend-architecture.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative reusable frontend component architecture for Nursilo V1 |
| Out of scope | Actual HTML; CSS; Tailwind classes; JavaScript; Alpine code; HTMX attributes; Django template source; Python; APIs; database; Figma; implementation artifacts |
| Nature | **Additive only** — does not modify locked docs `00`–`13` |

---

## 1. Purpose

Nursilo needs a **reusable component architecture** so public, student, assessment, library, and staff interfaces share one predictable UI vocabulary.

| Layer | Authority |
| --- | --- |
| [`12-design-system.md`](12-design-system.md) | Visual language |
| [`13-frontend-architecture.md`](13-frontend-architecture.md) | Frontend technology & boundaries |
| **This document** | Reusable component taxonomy, composition, states, and contracts |
| Future implementation | Templates / HTMX / Alpine / Tailwind mapping |

Benefits: consistent UX, accessibility consistency, reduced duplication, responsive consistency, and shared behavior across surfaces—without embedding business logic in components.

```text
12 Design System
    ↓
13 Frontend Architecture
    ↓
14 Component Architecture
    ↓
Future implementation
```

---

## 2. Component Architecture Principles

| Principle | Meaning |
| --- | --- |
| Reuse before duplication | Prefer existing vocabulary |
| Single responsibility | One clear job per component |
| Composition over monoliths | Build pages from smaller parts |
| Accessibility by default | Names, focus, keyboard included |
| Server truth | Components display server state |
| Minimal client behavior | Alpine/HTMX enhance only |
| Design-system alignment | Follow docs/12 |
| Responsive by default | Mobile-first adaptation |
| Localization-safe | Bangla/English length tolerance |
| State-complete | Meaningful states defined |
| No business logic | No scoring, workflow, or pricing rules |
| No authorization logic | No RBAC decisions |
| No entitlement authority | Display only |
| No persistence logic | No repository/data writes |
| Predictable naming | Purpose-first names |
| Testability | States and contracts are testable |

---

## 3. Component Hierarchy

| Level | Role | Examples |
| --- | --- | --- |
| **Foundation** | Layout/typography primitives | Surface, Stack, Icon |
| **Primitive** | Smallest interactive/display units | Button, Input, Badge |
| **Composite** | Primitive combinations | FormField, SearchField, Pagination |
| **Pattern** | Recurring UI solutions | DataTable, FilterBar, NotificationPanel |
| **Section** | Page region assemblies | DashboardSection, ExamQuestionPanel |
| **Page** | Full route compositions | StudentDashboard, ExamSession, BookReader |

Not every page should become a reusable component. Pages compose sections; only shared UI becomes vocabulary.

Preferred composition direction:

```text
Page → Section → Pattern → Composite → Primitive
```

---

## 4. Component Taxonomy

| Family | Purpose | Typical usage | Allowed | Forbidden |
| --- | --- | --- | --- | --- |
| **A. Foundation** | Structural/visual base | Layout rhythm | Spacing, surfaces | Domain rules |
| **B. Navigation** | Wayfinding | Headers, sidebars | Render supplied nav | Permission calculation |
| **C. Actions** | Triggers | Buttons, links | Hierarchy/states | Auto-authorize |
| **D. Forms** | Data entry | Auth, profile, filters | Labels, validation display | Persist independently |
| **E. Feedback** | System messages | Alerts, toasts | Severity presentation | Secrets |
| **F. Data display** | Lists/tables/stats | Catalogs, admin lists | Presentation | Query repositories |
| **G. Content** | Generic content blocks | CMS/marketing | Structure | SEO policy invention |
| **H. Assessment** | Practice/exam UI | Sessions, review | Represent attempt UI | Score/timer authority |
| **I. Learning** | Hierarchy & progress | Courses, lessons | Display progress | Mutate progress alone |
| **J. Library** | Books/reader | Catalog, reader | Access state display | Entitlement decisions |
| **K. Subscription** | Plans/billing UX | Upgrade, status | Honest states | Fake urgency / confirm payment |
| **L. Notifications** | Alerts & announcements | Bell, lists | Read/unread UI | Expose tokens |
| **M. Staff/Admin** | Operational tools | Queues, tables | RBAC-supplied actions | Bypass RBAC |
| **N. System/Error** | Failures & system | 404/403/500 | Safe messaging | Leak internals |
| **O. Accessibility helpers** | A11y utilities | Visually hidden, focus | Assistive support | Decorative misuse |

---

## 5. Foundation Components

Conceptual: Icon, Text, Heading, Divider, Container, Stack, Grid, Surface, Badge base, Visually hidden content, Focus indicator.

Remain domain-neutral and implementation-neutral.

---

## 6. Navigation Components

Header; Public navigation; Student navigation; Staff sidebar; Mobile navigation; Breadcrumbs; Tabs; Pagination; Back navigation; Footer; User menu; Language switcher; Notification entry.

**RBAC rule:** Components render only navigation data supplied by the server/presentation layer. They must never determine permissions. Inaccessible modules must not appear as available.

---

## 7. Action Components

Primary, Secondary, Tertiary/ghost, Danger, Link action, Icon button, Button group, Submit action, Loading action.

| Concern | Rule |
| --- | --- |
| Hierarchy | Normally one dominant primary per focused region |
| States | Default, hover, focus, active, disabled, loading |
| Accessibility name | Required, especially icon-only |
| Destructive | Confirmation required for critical actions |

---

## 8. Form Components

Form, Field, Label, Input, Password input, Textarea, Select, Checkbox, Radio, Toggle, Search field, File upload, Help text, Validation message, Form summary.

| Rule |
| --- |
| Labels are persistent (not placeholder-only) |
| Validation display is server-authoritative |
| Errors are localized |
| Sensitive fields follow security UX |
| No permission decisions inside form components |
| No independent persistence |

---

## 9. Feedback Components

Alert, Toast, Inline success/error, Warning, Information, Security alert, Entitlement notice, Payment status, Maintenance notice.

Severity must be accessible (text/icon + color). Never expose secrets.

---

## 10. Data-Display Components

| Component | Use when | Avoid when |
| --- | --- | --- |
| Card | Interactive grouping helps | Decorating every block |
| List / Table / Data row | Scannable collections; staff density | Tiny unreadable learner tables |
| Metadata block | Book/course facts | Long essay content |
| Stat | Dashboard metrics | Replacing narrative results |
| Badge / Status indicator | Semantic states | Color-only meaning |
| Empty / Loading / Skeleton / Error | System honesty | Fake content |
| Pagination / Filter bar | Large collections | Exams that need focus mode |

---

## 11. Modal / Overlay Components

Modal, Confirmation dialog, Drawer, Popover, Dropdown, Tooltip.

| Rule |
| --- |
| Focused tasks only |
| Keyboard accessible + focus management |
| No modal stacks unless explicitly justified |
| Essential information cannot exist only in a tooltip |

---

## 12. Learning Components

Course item; Subject/Unit/Chapter/Topic navigators; Lesson item; Lesson progress; Continue Learning; Progress indicator; Learning material block; Study goal; Weak/strong topic indicator; Recent activity.

Hierarchy must match [`05`](05-domain-model.md), [`09`](09-business-rules.md), [`11`](11-ui-ux-specification.md), [`12`](12-design-system.md).

---

## 13. Assessment Components

Question stem; Answer option; Answer group; Question navigator; Progress indicator; Timer display; Flag/review control; Submit confirmation; Exam/Practice header; Result summary; Score summary; Review item; Explanation panel; Attempt status.

| Server owns | Timer truth; attempt state; submission; scoring; question version; completion |
| --- | --- |

Components only represent server-provided state. Client timer is display assistance only.

---

## 14. Library Components

Book card; Book metadata; Book detail header; Premium badge; Access state; Reader toolbar; Reader content region; Bookmark action; Download action; Library filters; Library empty state.

Entitlement remains server authoritative. Storage keys/URLs are not authorization.

---

## 15. Subscription / Payment Components

Plan card; Current plan status; Premium badge; Upgrade CTA; Payment status; Pending/Success/Failure states; Billing summary.

| Rule |
| --- |
| Never fake urgency |
| Never misrepresent entitlement |
| Payment result from server truth only |
| No optimistic payment confirmation |
| Avoid unnecessary sensitive payment details |

---

## 16. Notification Components

Notification indicator; Notification list; Notification item; Read/unread state; Announcement item; Security notification; Priority marker; Notification empty state.

Never display passwords, tokens, session identifiers, or secret recovery information.

---

## 17. Staff / Admin Components

Admin sidebar; Role-aware navigation; Data table; Filter bar; Search/filter controls; Editorial status badge; Review queue item; Approval/rejection action; Publishing control; Audit log row; Bulk action toolbar; Import progress; Report summary; Operational alert.

Components must not bypass RBAC. Actions shown must be supplied as permitted by the presentation/service boundary.

---

## 18. Error / System Components

404, 403, 500, Session expired, Maintenance, Offline/best-effort, Generic error, Validation error.

No sensitive information leakage; provide recovery paths where appropriate.

---

## 19. Component States

Applicable interactive components define meaningful subsets of:

Default, Hover, Focus, Active, Disabled, Loading, Success, Error, Empty, Selected, Expanded, Collapsed, Read, Unread, Locked, Premium, Free.

Not every component needs every state. States must be accessible (not color-only).

---

## 20. Responsive Component Behavior

| Viewport | Expectations |
| --- | --- |
| Mobile | Touch-friendly options; stacked forms; collapsed nav |
| Tablet | Comfortable reading/exam |
| Desktop / large | Denser staff tables; optional multi-column learning |

Navigation collapses appropriately; tables may scroll or transform; exam controls remain visible; reader prioritizes content; staff density must remain accessible.

---

## 21. Accessibility Contract

Every component conceptually defines: accessible name; keyboard behavior; focus behavior; screen-reader behavior; state communication; error communication; color-independent meaning; reduced-motion behavior; touch target expectations.

Follow [`11`](11-ui-ux-specification.md) and [`12`](12-design-system.md).

---

## 22. Localization Contract

Components must tolerate Bangla, English, mixed language, longer strings, localized dates/numbers/currency, and medical English inside Bangla UI.

Do not assume fixed string lengths. Do not hard-code UI language into component architecture.

---

## 23. HTMX Component Boundary

| Allowed enhancements | Pagination; filters; search; bookmark toggle; notification read state; inline form updates; modal content; staff queue updates |
| --- | --- |

| HTMX must not own | Authorization; entitlement; scoring; payment truth; session truth |
| --- | --- |

Server responses determine resulting component state.

---

## 24. Alpine Component Boundary

| Allowed | Dropdowns; tabs; disclosure; modal visibility; local UI state; password visibility; visual countdown display; temporary interaction |
| --- | --- |

Alpine must never become business authority.

---

## 25. Component Data Contract

Components receive conceptually: display data; state; labels; accessibility metadata; URLs/actions; permission-aware presentation data.

They must not query repositories or independently calculate business permissions.

---

## 26. Component Composition Rules

| Prefer | Page → Section → Pattern → Composite → Primitive |
| --- | --- |

Define parent-child responsibilities, one-way data/action flow, clear state ownership, reusable composition, no circular dependencies, no giant components, no needlessly deep trees.

---

## 27. Component Naming Conventions

Names describe purpose and domain (and state only when needed).

| Good | Avoid |
| --- | --- |
| ExamTimer, QuestionOption, BookCard, NotificationItem, EntitlementNotice | GreenBox, BigCard, Thing, Widget1 |

Avoid vague names, visual-only names, duplicate synonyms, and framework-specific names in the architecture vocabulary.

---

## 28. Component Dependency Rules

Allowed direction: Page → Section → Pattern → Composite → Primitive.

Lower-level components must not import page/domain concepts unnecessarily. Primitives remain domain-neutral. Assessment components may compose primitives but must not contain scoring logic.

---

## 29. Component Reuse Rules

Before creating a new component:

1. Search existing vocabulary  
2. Prefer supporting the need with an existing component  
3. Extend only when semantics remain coherent  
4. Create new only when reuse reduces clarity  
5. Document meaningful new patterns  

Discourage one-off components.

---

## 30. Design System Alignment

Every component aligns with docs/12 for typography, color semantics, spacing, radius, elevation, iconography, status, motion, accessibility, and premium presentation.

No component may introduce an independent visual language.

---

## 31. Security-Aware Components

Safe presentation for session expiry, device management, logout all, password change, email verification, re-authentication, premium purchase, suspended account, permission denial, and security notifications.

Never expose secrets, tokens, passwords, session identifiers, internal paths, or sensitive payment data.

---

## 32. Component Testing Strategy

Conceptual tests: rendering; accessibility; keyboard; responsive behavior; state transitions; validation display; HTMX enhancement; Alpine enhancement; localization; entitlement presentation; assessment presentation; error states; regression.

Component tests do **not** replace service/domain tests.

---

## 33. Component Performance

Avoid unnecessary client JavaScript and excessive DOM complexity; avoid redundant requests; use partial updates appropriately; lazy-load only where beneficial; avoid oversized images; keep critical assessment UI lightweight.

---

## 34. Component Documentation

Future implemented components should document: purpose, usage, variants, states, accessibility, responsive behavior, localization, HTMX/Alpine behavior if applicable, known limitations.

Do not generate actual component documentation files now.

---

## 35. Future Component Extensions

**Future-only:** Flutter equivalents; dark mode; AI Tutor components; adaptive learning components; offline indicators; institution components; advanced visualization.

These must not silently become V1 requirements.

---

## 36. Component Governance

Ownership; review; accessibility gate; visual consistency gate; security review where relevant; breaking changes; deprecation; duplicate prevention; technical debt.

New components require justification.

---

## 37. Cross References

| Document | Relationship |
| --- | --- |
| [`03`](03-user-roles.md) | RBAC-aware presentation |
| [`04`](04-system-architecture.md) | Service authority |
| [`05`](05-domain-model.md) | Learning/assessment structure |
| [`07`](07-security-and-session-management.md) | Security-aware components |
| [`08`](08-api-design.md) | Future client parity |
| [`09`](09-business-rules.md) | Behavioral truth outside components |
| [`11`](11-ui-ux-specification.md) | Experience patterns |
| [`12`](12-design-system.md) | Visual system |
| [`13`](13-frontend-architecture.md) | Technology boundaries |

**This document does not modify any approved document.**

---

## 38. Acceptance Criteria

This document is acceptable when:

1. Component hierarchy and taxonomy are defined  
2. Foundation, navigation, action, form, feedback, data-display, and modal/overlay components are defined  
3. Learning, assessment, library, subscription/payment, notification, staff/admin, and error/system components are defined  
4. Component states, responsive behavior, accessibility, and localization contracts are defined  
5. HTMX and Alpine boundaries are defined  
6. Data contracts, composition, dependency, naming, and reuse rules are defined  
7. Design-system alignment and security-aware rules are defined  
8. Testing, performance, documentation expectations, governance, and Future-only extensions are defined  
9. **No** HTML/CSS/JS/HTMX/Alpine/Django template/source code is generated  
10. **No** API/database implementation is generated  
11. Docs `00`–`13` remain unchanged  

---

## 39. Document Lock

**Status:** `docs/14-frontend-component-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative reusable frontend component architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`13` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*
