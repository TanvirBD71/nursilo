# Nursilo — Design System

| Field | Value |
| --- | --- |
| Document | `12-design-system.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`11`](11-ui-ux-specification.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative visual design system for Nursilo Version 1 |
| Out of scope | Implementation code; CSS; HTML; Tailwind; JavaScript; templates; Figma; APIs; database; ORM; migrations; framework-specific component code |
| Nature | **Additive only** — does not modify locked docs `00`–`11` |

---

## 1. Purpose

Nursilo needs a unified design system so public marketing, learner study flows, assessment sessions, library reading, and staff tools share one coherent visual language.

| Authority | Owns |
| --- | --- |
| [`11-ui-ux-specification.md`](11-ui-ux-specification.md) | Experience, journeys, information architecture, interaction behavior |
| **This design system** | Visual language, semantic surfaces, typography, spacing, and reusable design patterns |
| Later implementation specs | Framework mapping (templates, CSS, Flutter themes)—**not this document** |

The design system:

- Prevents one-off visual decisions that fragment the product  
- Supports future web, Flutter, desktop, and other clients through conceptual patterns—not framework lock-in  
- Treats accessibility and Bangla/English localization as first-class design concerns  

It defines **WHAT** the visual system is and **WHY**—not **HOW** it is coded.

---

## 2. Design System Principles

| Principle | Nursilo context |
| --- | --- |
| **Consistency** | Same button, form, status, and exam patterns everywhere |
| **Simplicity** | Prefer clear hierarchy over decorative complexity |
| **Accessibility** | Contrast, focus, and non-color status communication by default |
| **Educational clarity** | Hierarchy and question text stay readable under stress |
| **Trust** | Honest Free/Premium states; calm security messaging |
| **Professionalism** | Credible for nursing exams—not playful gamification |
| **Calmness** | Study and exam surfaces reduce visual noise |
| **Reusability** | Patterns compose across public, learner, and staff UIs |
| **Scalability** | Works for growing content volume and future clients |
| **Responsive-first thinking** | Mobile learner flows are first-class |
| **Bangladesh-first localization** | Bangla/English length, numerals, and cultural imagery |
| **Performance awareness** | Visual richness must not imply heavy unnecessary assets |
| **Progressive disclosure** | Advanced filters/analytics appear when needed |
| **Honest premium presentation** | No dark patterns or fake urgency |
| **Minimal cognitive load** | One dominant action per focused region |

---

## 3. Brand Identity

| Element | Definition |
| --- | --- |
| **Brand** | Nursilo |
| **Tagline** | Learn. Practice. Succeed. |

| Aspect | Specification |
| --- | --- |
| **Personality** | Competent, supportive, serious about exam success |
| **Character** | Clinical clarity with human warmth—not cold bureaucracy |
| **Professional tone** | Suitable for students, interns, and registered nurses |
| **Educational tone** | Structured learning and deliberate practice |
| **Trust signals** | Clear entitlements, stable results, security transparency |
| **Emotional impression** | Confidence through preparation—not hype |
| **Public-facing brand** | Stronger brand expression on marketing/home surfaces |
| **In-app learning behavior** | Calm, focused, content-first; brand present but not loud |

Avoid playful/gamified chrome that distracts from nursing education and high-stakes exam preparation. There is no certificate-celebration visual language in V1.

---

## 4. Brand Color System

No hex/CSS/Tailwind tokens are defined here. Earlier approved docs did **not** lock a numeric palette; this system establishes **semantic roles** and conceptual hue guidance.

**Conceptual brand direction:** a calm **clinical teal / deep sea-green** primary (trust, care, focus) with **neutral ink** text on **cool off-white / soft slate** surfaces—distinct from generic purple SaaS themes and warm terracotta “AI default” looks. Exact values are chosen at implementation time under accessibility review.

### 4.1 Brand vs semantic colors

| Class | Role |
| --- | --- |
| **Brand colors** | Identity, primary actions, links, selection accents |
| **Semantic status colors** | Success, warning, danger, information |

Brand color must **not** replace success/error/warning semantics.

### 4.2 Semantic palette

| Category | Purpose | Appropriate usage | Inappropriate usage | Accessibility |
| --- | --- | --- | --- | --- |
| **Primary** | Brand identity & main CTAs | Primary buttons, key links, active nav | Error states; large background floods in exams | Pair with sufficient contrast on surfaces |
| **Secondary** | Supporting emphasis | Secondary buttons, charts accents | Competing with Primary on same task | Keep subordinate to Primary |
| **Accent** | Sparse highlight | Premium cue companion, rare highlights | Entire themes; status meaning alone | Never sole meaning carrier |
| **Background** | Page canvas | App/page backdrop | Text color | Calm, low chroma |
| **Surface** | Default content panels | Forms, sections | Decorative noise | Distinguish from Background |
| **Elevated Surface** | Overlay hierarchy | Modals, popovers, sticky bars | Nested elevation stacks | Clear edge/contrast vs Surface |
| **Text Primary** | Main reading text | Stems, titles, body | Disabled text | Highest contrast on Surface |
| **Text Secondary** | Supporting copy | Descriptions, meta | Critical errors | Still readable |
| **Text Muted** | Low emphasis | Hints, timestamps | Primary instructions | Meet muted-text contrast floor |
| **Border** | Structure | Inputs, table lines | Heavy boxes everywhere | Visible without harshness |
| **Divider** | Separation | Section rules | Replacing spacing systems | Subtle vs Border |
| **Success** | Positive outcome | Save OK, correct (with icon/text) | Brand decoration | Not color-only |
| **Warning** | Caution | Time low, pending payment | Marketing urgency fakes | Pair with label/icon |
| **Danger** | Destructive/critical | Logout all, archive confirm, incorrect | Ordinary CTAs | High clarity + confirmation |
| **Information** | Neutral notice | Tips, system info | Errors | Distinct from Warning |
| **Disabled** | Unavailable | Disabled controls | Softening errors | Reduced contrast but still identifiable |
| **Premium** | Paid capability | Badges, locked teasers | Fake scarcity | Understandable without hue alone |
| **Free** | Free-tier state | Plan badge | Shaming Free users | Neutral, respectful |

---

## 5. Color Accessibility

| Requirement | Specification |
| --- | --- |
| Contrast expectations | Align with WCAG 2.x AA-oriented guidance from [`11`](11-ui-ux-specification.md) |
| Text contrast | Body and UI text meet AA against their surfaces |
| Large text contrast | Large titles meet large-text thresholds |
| UI component contrast | Icons/borders of interactive controls remain perceivable |
| Focus visibility | Focus rings clearly visible on all interactive elements |
| Disabled treatment | Visibly disabled without looking like an error |
| Status meaning | Status colors never the only source of meaning |
| Color-blind-safe communication | Icons, labels, and patterns reinforce status |
| Premium indicators | Understandable without relying only on gold/brand hue |

---

## 6. Typography System

| Role | Hierarchy intent |
| --- | --- |
| **Display** | Rare marketing hero expression |
| **H1** | Page title |
| **H2** | Major section |
| **H3** | Subsection |
| **H4** | Minor grouping |
| **Body large** | Emphasized reading |
| **Body** | Default content |
| **Body small** | Compact secondary |
| **Caption** | Meta, timestamps |
| **Label** | Form labels |
| **Button text** | Action labels |
| **Numeric/statistical text** | Scores, timers, stats—tabular clarity |
| **Exam question text** | Highest readability in assessment |
| **Exam answer text** | Clear option labels; selectable comfort |

| Principle | Specification |
| --- | --- |
| Hierarchy | One clear page H1; avoid competing display sizes in-app |
| Readability | Prefer comfortable sizes for long nursing content |
| Line length | Limit long-form measure for lessons and explanations |
| Line height | Generous for Bangla/English stems; tighter for dense admin tables |
| Weight | Regular body; medium/semibold for emphasis and buttons |
| Emphasis | Prefer weight/structure over decorative underlines |
| Long-form reading | Calm, distraction-free lesson/material presentation |
| Exam readability | Question stem dominates; chrome minimized |

---

## 7. Bengali + English Typography

| Concern | Specification |
| --- | --- |
| Bangla principles | Ensure script clarity at body and exam sizes; avoid overly condensed Bangla display faces for stems |
| English principles | Neutral professional sans for UI; readable for clinical English |
| Mixed text | Layout must tolerate mixed Bangla/English in one sentence |
| Numerals | Consistent numeral style within a locale context |
| Medical/nursing terms | Prefer clarity over stylistic flourish; allow Latin clinical terms inside Bangla UI |
| Long Bangla labels | Nav/buttons wrap or truncate with accessible full labels |
| Length variance | English short / Bangla long must not break components |
| Font fallback philosophy | Define a stack conceptually: preferred Bangla-capable UI face → system fallbacks; no framework loading rules here |
| Layout breakage | Test critical flows with longest expected Bangla strings |

RTL remains outside V1.

---

## 8. Spacing System

Conceptual scale (not CSS tokens): micro → component → section → page.

| Context | Spacing philosophy |
| --- | --- |
| **Micro** | Icon-to-label, badge padding |
| **Component** | Field stacks, button groups |
| **Section** | Dashboard widget separation |
| **Page** | Top/bottom page rhythm |
| **Dashboard** | Primary actions get air; secondary denser |
| **Exam** | Focus on stem/options; reduce peripheral gaps noise |
| **Admin density** | Tighter, still scannable |
| **Mobile** | Larger touch-friendly gaps |
| **Desktop** | Efficient use of width without sparse emptiness |

Supports **calm learner** and **dense staff** modes without two unrelated systems.

---

## 9. Layout & Grid System

| Concern | Specification |
| --- | --- |
| Page container | Centered content with consistent horizontal inset |
| Max readable width | Constrain lesson/exam reading measure; allow wider admin tables |
| Full-width surfaces | Marketing heroes, some dashboard bands |
| Content columns | Single column mobile; progressive multi-column desktop where helpful |
| Sidebar layouts | Staff tools; optional learner section nav |
| Dashboard grids | Priority-ordered regions (see §25), not equal card tiles |
| Assessment layouts | Stem + options primary; nav/timer secondary |
| Library layouts | Catalog grid/list adaptable; reader immersion |
| Admin layouts | Sidebar + dense main |
| Mobile / tablet / desktop / large | Progressive disclosure of density; no broken exam chrome |

Exam interfaces prioritize focus and readability over branding spectacle.

---

## 10. Border, Radius & Elevation Language

| Element | Rule |
| --- | --- |
| Borders | Subtle structural lines; not heavy frames on every block |
| Dividers | Prefer spacing + light dividers over boxes |
| Corner radius | Modest, consistent; avoid “pill everything” |
| Elevation | Use sparingly for modals, sticky bars, popovers |
| Shadows | Soft and rare; not multi-layer fashion stacks |
| Surface hierarchy | Background < Surface < Elevated |

Avoid excessive rounded-card design. Nursilo must not depend on cards for every content fragment. Elevation communicates hierarchy or interaction—not decoration.

---

## 11. Iconography

| Aspect | Specification |
| --- | --- |
| Style | Simple, geometric, professional line icons (consistent stroke) |
| Consistency | One family; avoid mixing filled/outline randomly |
| Sizing | Align to text/control sizes conceptually (nav, inline, status) |
| Domains | Distinct metaphors for learn, practice, exam, library, security, notify, admin |
| Rules | Icons support meaning; do not replace necessary text |
| Decorative icons | Must not create screen-reader noise |
| Emoji | Not core UI iconography |

---

## 12. Illustration System

| Characteristic | Educational, clean, modern, professional, human-centered, calm, inclusive, minimal |
| --- | --- |

| Appropriate | Empty states, marketing, onboarding, light educational explanation, some error empathy |
| --- | --- |
| Avoid | Illustration overload inside focused study/exam flows |

---

## 13. Photography & Image Guidelines

| Area | Guidance |
| --- | --- |
| Nursing/medical imagery | Accurate, respectful clinical/education contexts |
| Student imagery | Diverse, inclusive, Bangladesh-relevant where possible |
| Book covers | True covers; no misleading placeholders as final |
| Course/CMS/marketing | Real educational atmosphere; avoid stock cliché that weakens trust |
| Quality | Sharp, well-lit, consistent crop |
| Cropping | Faces and critical diagram regions protected |
| Accessibility text | Meaningful alternatives for informative images; decorative marked appropriately |
| Misleading imagery | No fake “certificates,” false credentials, or sensational medical shock |
| Cultural appropriateness | Respectful for Bangladesh audiences |

---

## 14. Component Design Language

Conceptual families (purpose / hierarchy / usage / a11y / misuse):

| Family | Purpose | Hierarchy / usage notes | Avoid |
| --- | --- | --- | --- |
| **Buttons** | Actions | See §15 | Multiple primaries |
| **Links** | Navigation | Inline vs standalone | Fake buttons |
| **Inputs / selects / checkboxes / radios / toggles / textareas** | Data entry | Clear labels | Placeholder-as-label |
| **Search fields** | Discovery | Prominent in learner chrome | Hidden critical search |
| **Cards** | Interactive grouping | Only when interaction benefits | Card-everything |
| **Tables** | Dense data | Staff-first | Tiny unreadable learner tables |
| **Tabs** | Peer sections | Few tabs | Deep nesting |
| **Breadcrumbs** | Hierarchy location | Learning/admin trees | Replacing primary nav |
| **Pagination** | List traversal | Predictable | Infinite scroll for exams |
| **Badges / chips** | Status/tags | Semantic (§19) | Color-only status |
| **Alerts / notifications** | Feedback | Calm severity | Alarmist copy |
| **Dialogs / drawers** | Focused tasks | Confirmations | Navigation via modal stacks |
| **Tooltips / dropdowns** | Progressive disclosure | Keyboard accessible | Essential-only-in-tooltip |
| **Navigation / sidebars / headers / footers** | Wayfinding | RBAC-aware | Showing forbidden modules |
| **Progress / loading / skeleton / empty** | System state | Honest feedback | Fake progress |

---

## 15. Button System

| Variant | Role |
| --- | --- |
| Primary | Single dominant action in a focused area |
| Secondary | Alternative common action |
| Tertiary / Outline / Ghost | Low emphasis |
| Danger | Destructive/critical |
| Link-style | Navigational action looking like text link |
| Icon-only | Must have accessible name |
| Disabled / Loading | Non-interactive / in-flight |

| Hierarchy rule | Normally **one** visually dominant primary action per focused region |
| --- | --- |

Critical actions—submit exam, logout all devices, archive, delete where permitted, confirm payment—use confirmation patterns and danger semantics where appropriate.

---

## 16. Form Design System

| Element | Rule |
| --- | --- |
| Labels | Visible, persistent; not placeholder-only |
| Required / optional | Clearly indicated |
| Placeholders | Examples only, not labels |
| Help text | Short, localized |
| Validation | Inline + summary when needed; server authoritative |
| Error / success / warning | Distinct, accessible |
| Disabled / read-only | Visually distinct |
| Password / sensitive | Masking + re-auth patterns per security UX |
| File uploads | Clear type/size expectations; progress for large staff uploads |
| Locale | Usable in Bangla and English lengths |

---

## 17. Data Table Design

| Concern | Specification |
| --- | --- |
| Hierarchy | Header clarity; sticky header when long |
| Column priority | Important columns first; progressive hide on small screens |
| Sort / filter / pagination | Visible affordances |
| Row / bulk actions | Explicit; confirm destructive bulk |
| Selection | Clear selected state |
| Status indicators | Badge + text |
| Responsive | Horizontal scroll or stacked alternatives |
| Empty / loading / error | Actionable empty; skeleton/loading; recoverable error |
| Density | Staff dense; learner-facing tables remain readable |

---

## 18. Cards & Content Containers

| Appropriate | Courses, lessons, books, question summaries, dashboard summaries, analytics blocks, notification items—when grouping aids interaction |
| --- | --- |

| Discourage | Card-everything layouts; decorative containers without interaction value; excessive shadows; excessive borders |
| --- | --- |

---

## 19. Badges, Chips & Status

Semantic patterns include: Free, Premium, Draft, Review, Approved, Published, Archived, Easy, Medium, Hard, Expert, In Progress, Completed, Failed, New, Unread.

Status must remain understandable **without color alone** (label and/or icon required).

---

## 20. Feedback & Alert System

| Type | Use |
| --- | --- |
| Informational | Tips, neutral system notes |
| Success | Completed save/submit |
| Warning | Caution, approaching timeout |
| Error | Failures, validation |
| Security alert | Device/session/password events—calm, actionable |
| Entitlement denial | Honest lock + upgrade path |
| Payment status | Pending/confirmed/failed without sensitive details |
| Validation | Field-adjacent |
| Maintenance | System-wide notice |

Never expose passwords, tokens, session identifiers, stack traces, internal paths, or sensitive payment data.

---

## 21. Loading, Empty & Error States

| State | Guidance |
| --- | --- |
| Loading / Skeleton | Prefer skeletons for dashboards/catalogs |
| Empty / no search / no notifications / no bookmarks / no attempts / no progress | Explain next useful action |
| Permission denied | Clear 403-style messaging; no leakage |
| Entitlement denied | Honest premium/free explanation |
| Session expired | Re-auth path |
| Server error | Generic apology |
| Maintenance / offline best-effort | Honest system state |

---

## 22. Assessment Design System

| Element | Visual principle |
| --- | --- |
| Practice / Exam | Focus mode; reduced chrome in live exams |
| Question stem | Highest contrast and size priority |
| Answer options | Large hit targets; clear selected state |
| Correct / incorrect | Icon + text + color; never color-only |
| Flag / review later | Optional, visible |
| Question navigation | Position clarity |
| Progress / timer | Visible, calm; warning near end |
| Submission | Confirmation; then immutable completed messaging |
| Results / review | Scannable summary; explanation panels when allowed |

Minimize cognitive load. Server truth remains authoritative for timers and results.

---

## 23. Learning Experience Design System

Visual patterns must keep Course → Subject → Unit → Chapter → Topic → Lesson → Learning Material understandable via breadcrumbs, section titles, and progress cues. Continue Learning is visually primary on the student home. Weak/strong topics use clear semantic markers without alarming styling.

---

## 24. Library Design System

| Pattern | Rule |
| --- | --- |
| Book cards / detail | Cover + metadata + honest Premium badge |
| Reading | Immersive, low chrome |
| Download | Only when allowed; clear deny |
| Bookmark | Easy return |
| Access denied / empty | Actionable, non-shaming |

Premium presentation is honest and non-manipulative.

---

## 25. Dashboard Design System

### Student dashboard visual priority

1. Continue Learning  
2. Today’s Goal  
3. Primary study action  
4. Progress  
5. Exam history  
6. Weak/strong topics  
7. Bookmarks  
8. Notes  
9. Activity  
10. Streak  
11. Subscription  
12. Notifications  

### Staff dashboards

Operational summaries, queues, alerts, content workflow, reports—dense but accessible.

---

## 26. Navigation Design System

| Surface | Rules |
| --- | --- |
| Public / student / staff sidebar | Clear active and focus states; RBAC-filtered |
| Breadcrumbs | Hierarchy orientation |
| Mobile navigation | Reachable primary destinations |
| Current location | Always evident |
| Back navigation | Predictable in nested learning/admin |
| Exam focus mode | Minimal chrome; retain submit/exit clarity |

Inaccessible modules must not appear as available actions.

---

## 27. Notification Design System

| Type | Treatment |
| --- | --- |
| In-app / announcements | Distinct when helpful |
| Security | Clear, calm, actionable, non-alarming |
| Success / warning / critical | Severity-aligned styling + text |
| Read/unread / priority | Visible indicators |

Never expose secrets.

---

## 28. Motion & Animation Principles

| Allow | Purposeful transitions, modal enter/exit, loading feedback, subtle success, progress, micro-interactions |
| --- | --- |
| Respect | Reduced-motion preference |
| Never interfere with | Reading, exam answering, timer awareness, accessibility |

---

## 29. Responsive Design System

| Viewport | Priority |
| --- | --- |
| Mobile | Learner practice/exam/continue/checkout-critical flows |
| Tablet | Comfortable reading and exams |
| Laptop / Desktop / Large | Admin density; optional multi-column learning |

Ensure touch targets, reading width, exam controls, navigation, tables, forms, and dialogs remain usable.

---

## 30. Accessibility Design System

WCAG 2.x AA-oriented design covering contrast, focus, keyboard, screen readers, labels, semantic meaning, status communication, touch targets, reduced motion, text resizing, zoom, and error identification.

Accessibility is **not** optional.

---

## 31. Localization Design System

Bangla and English support for mixed language, text expansion/wrapping, date/number/currency formats, medical terminology, search, errors, and navigation labels. RTL remains outside V1 unless separately approved.

---

## 32. Security-Aware Design

Align with [`07`](07-security-and-session-management.md) and [`09`](09-business-rules.md) for visual treatment of: session expiry, device management, logout all, password change, email verification, password reset, re-authentication, premium purchase, suspended account, permission denial, and security notifications.

Security UX must not reveal sensitive information.

---

## 33. Premium / Freemium Design Language

| State | Presentation |
| --- | --- |
| Free / Premium / Locked / Unavailable | Truthful badges and copy |
| Upgrade opportunity | Clear value; no coercion |

Rules: no dark patterns, misleading buttons, fake urgency, or deceptive countdowns; explain restrictions; show premium indicators before avoidable friction; entitlement state always truthful.

---

## 34. Design System Governance

| Concern | Conceptual rule |
| --- | --- |
| Ownership | Product/design authority maintains this system in alignment with Super Admin platform governance—without inventing roles that contradict [`03`](03-user-roles.md) |
| Proposal / review | Visual changes proposed against this doc; reviewed for a11y and consistency |
| Breaking visual changes | Require explicit revision gate |
| Accessibility regressions | Block release conceptually until remediated |
| New components | Approved only if no existing pattern suffices |
| Duplicates | Actively discouraged |
| Consistency | Spot-check against learner exam and staff table surfaces |

---

## 35. Future Design System Extensions

**Future only:** dark mode, Flutter adaptation, desktop, AI Tutor, Adaptive Learning, Offline Mode, Institution Portal, advanced visualization, design-token implementation.

Future features must not silently become V1 requirements.

---

## 36. Cross References

| Document | Relationship |
| --- | --- |
| [`00`](00-project-vision.md)–[`02`](02-feature-list.md) | Brand, product scope |
| [`03`](03-user-roles.md) | What roles may see |
| [`07`](07-security-and-session-management.md) | Security-aware UX |
| [`09`](09-business-rules.md) | Entitlement and workflow truth |
| [`10`](10-development-roadmap.md) | Delivery sequencing |
| [`11`](11-ui-ux-specification.md) | Experience authority this visual system supports |

**This document does not modify any approved document.**

---

## 37. Acceptance Criteria

This document is acceptable when:

1. Brand identity and personality are defined  
2. Semantic color system is defined (brand vs status separated)  
3. Accessibility color guidance exists  
4. Typography hierarchy is defined  
5. Bangla and English typography considerations are defined  
6. Spacing and grid/layout philosophies are defined  
7. Iconography, illustration, and imagery guidance exist  
8. Component families, button hierarchy, forms, tables, and cards are defined conceptually  
9. Status/badge semantics and feedback systems are defined  
10. Loading/empty/error states are defined  
11. Assessment, learning, library, dashboard, navigation, and notification visual patterns are defined  
12. Motion, responsive, accessibility, localization, security-aware, and freemium visual rules are defined  
13. Governance and Future-only extensions are defined  
14. **No** HTML, CSS, Tailwind, JavaScript, Django templates, Figma, API, database, or source-code implementation exists  
15. Docs `00`–`11` remain unchanged  

---

## 38. Document Lock

**Status:** `docs/12-design-system.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative visual design system for Nursilo V1. Substantive content remains unchanged. Docs `00`–`11` remain unmodified. Next documentation proceeds only when explicitly requested. No implementation artifacts will be generated until separately requested.

---

*Nursilo — Learn. Practice. Succeed.*
