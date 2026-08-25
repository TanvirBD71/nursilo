# Nursilo — Frontend Styling Architecture

| Field | Value |
| --- | --- |
| Document | `17-frontend-styling-architecture.md` |
| Version | `1.0.0` |
| Status | **Approved v1.0.0 — LOCKED** |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`16`](16-frontend-template-architecture.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative conceptual styling architecture for Nursilo V1 — how the design system maps to Tailwind/CSS organization without prescribing source |
| Out of scope | Actual CSS; Tailwind classes; configuration files; HTML; JavaScript; Alpine; HTMX; Django templates; Python; APIs; database implementation; Figma; source code |
| Nature | **Additive only** — does not modify locked docs `00`–`16` |

---

## 1. Purpose

Nursilo requires a dedicated **styling architecture** so the visual language in [`12`](12-design-system.md) is applied consistently through templates, components, and pages—without inventing a second design system or embedding business logic in stylesheets.

| Layer | Authority |
| --- | --- |
| [`12`](12-design-system.md) | Visual language (semantic colors, type, spacing, motion) |
| [`13`](13-frontend-architecture.md) | Frontend technology & boundaries (including Tailwind direction) |
| [`14`](14-frontend-component-architecture.md) | Reusable component vocabulary |
| [`15`](15-frontend-page-architecture.md) | Page composition |
| [`16`](16-frontend-template-architecture.md) | Conceptual Django-template organization |
| **This document** | Conceptual styling organization, token mapping, and style responsibility rules |
| Future implementation | Actual Tailwind theme, CSS entrypoints, and utility usage |

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
17 Styling Architecture
    ↓
Future implementation
```

Goals: one visual language; predictable token → utility mapping; component-safe styling; accessibility-preserving contrast and focus; localization-safe layout; responsive consistency; assessment/reader focus styling; honest Free/Premium presentation; minimal custom CSS; no style-layer business rules.

This document defines **how styling is organized and constrained**. It does **not** generate CSS, Tailwind classes, or theme configuration.

---

## 2. Styling Architecture Principles

| Principle | Meaning |
| --- | --- |
| Design system is authoritative | Styles express docs/12; they do not redefine brand |
| Semantic tokens over ad-hoc values | Prefer named roles (Background, Primary, Danger) over one-off colors |
| Tailwind-first composition | Prefer utility composition mapped to tokens |
| Minimal custom CSS | Custom styles only when utilities cannot express a system need |
| Presentation only | Styles never encode authorization, entitlement, scoring, or payment truth |
| Server state drives appearance | Free/Premium/Locked/Error visuals reflect server-provided state |
| Accessibility by default | Contrast, focus rings, non-color status cues |
| Localization-safe | Bangla/English expansion; no English-width assumptions |
| Mobile-first | Base styles serve phones; enhance upward |
| Density by family | Marketing airy; assessment focused; staff denser—by design, not accident |
| Consistency over novelty | Reuse established surfaces, type scale, spacing |
| Avoid visual drift | No page invents a private palette |
| Prefer composition | Style via shared component contracts, not copy-paste utilities |
| Motion is purposeful | Align with docs/12 motion principles; honor reduced motion |
| Correctness over polish | Security and clarity outrank decorative styling |

---

## 3. Styling Layer Model

Conceptual layers:

```text
Design System Concepts (docs/12)
    ↓
Semantic Style Tokens (conceptual roles)
    ↓
Theme / Utility Mapping (future Tailwind theme)
    ↓
Primitive Styling
    ↓
Component Styling Contracts (docs/14)
    ↓
Section / Pattern Styling
    ↓
Page / Layout Family Styling (docs/15–16)
    ↓
State & Feedback Styling
```

| Layer | Responsibility |
| --- | --- |
| **Semantic tokens** | Named roles for color, type, space, radius, elevation, motion |
| **Theme mapping** | Future binding of tokens to Tailwind/CSS implementation |
| **Primitives** | Base text, surfaces, controls without domain meaning |
| **Components** | Documented visual contracts for reusable UI |
| **Pages/layouts** | Family density, chrome, reading measure |
| **States** | Loading, empty, error, locked, Free/Premium presentation |

No layer may become a hidden business-logic authority.

---

## 4. Styling Technology Direction

Aligned with [`13`](13-frontend-architecture.md):

| Concern | Direction |
| --- | --- |
| Primary styling system | **Tailwind CSS** mapped to the approved design system |
| Supplemental CSS | Rare, system-level only (e.g., base resets already covered by tooling; unavoidable print/reader needs) |
| Inline styles | Avoid except where tooling requires unavoidable dynamic values from server-safe attributes |
| CSS-in-JS / SPA style systems | Not V1 direction |
| Third-party UI kits | Do not introduce competing visual languages |

Package versions, `tailwind.config`, PostCSS, and build pipelines are **out of scope** for this document.

---

## 5. Semantic Token Architecture

Tokens are **conceptual roles**, not hex values or Tailwind class strings.

### 5.1 Color tokens

Map docs/12 brand vs semantic roles:

| Token role family | Examples of roles | Notes |
| --- | --- | --- |
| Brand | Primary, Primary emphasis, Link accent | Identity and primary actions |
| Surface | Background, Surface, Elevated surface | Calm, low-chroma canvases |
| Text | Text primary, Text secondary, Text muted, Text inverse | Readable hierarchy |
| Border / Divider | Border, Divider | Subtle separation |
| Status | Success, Warning, Danger, Information | Never brand-as-status |
| Focus | Focus ring | Visible keyboard focus |
| Premium | Premium accent (honest, non-manipulative) | Distinct from Success |

Status meaning must remain understandable **without color alone** (icon and/or text required).

### 5.2 Typography tokens

| Token role | Maps to docs/12 |
| --- | --- |
| Display / Hero | Marketing emphasis (brand-first, not overpowering) |
| Page title | Primary page heading |
| Section title | Section hierarchy |
| Body | Learning and general reading |
| Compact / Dense | Staff tables and operational UI |
| Caption / Meta | Secondary metadata |
| Medical / Mixed script | Bangla + English + terminology safety |

### 5.3 Spacing, sizing, radius, elevation

Conceptual scales only:

| Scale | Use |
| --- | --- |
| Micro → component → section → page | Spacing rhythm |
| Touch-friendly control sizes | Mobile assessment and forms |
| Radius language | Soft vs structural per docs/12 |
| Elevation language | Prefer light elevation; avoid multi-layer shadow noise |

### 5.4 Motion tokens

| Token role | Use |
| --- | --- |
| Duration short / medium | Feedback, disclosure |
| Easing calm | Non-playful educational motion |
| Reduced-motion equivalent | Instant or minimal transition when requested |

Do **not** define millisecond values or CSS keyframes here.

---

## 6. Design-System → Styling Mapping

| docs/12 concept | Styling architecture responsibility |
| --- | --- |
| Brand identity | Brand token roles + public layout chrome |
| Semantic colors | Status/surface/text token families |
| Typography system | Type token roles + reading measure constraints |
| Bangla + English | Font stack strategy (conceptual); expansion-safe layouts |
| Spacing / grid | Spacing tokens; layout family width rules |
| Borders / radius / elevation | Surface language consistency |
| Iconography | Size/alignment contracts; status icons with labels |
| Buttons / forms / tables | Component styling contracts |
| Assessment design | Focus layout density; timer/option clarity |
| Library / reader | Content-first measure; minimal chrome |
| Dashboard | Visual priority order preserved in spacing hierarchy |
| Motion | Purposeful, reduced-motion compatible |
| Premium / freemium | Honest locked/Premium presentation tokens |
| Accessibility | Contrast, focus, non-color status |

No styling artifact may introduce an independent visual language.

---

## 7. Layout Family Styling

| Family | Styling emphasis |
| --- | --- |
| **Public / Marketing** | Brand-first hero plane; airy spacing; strong CTA contrast; SEO-friendly hierarchy |
| **Authentication** | Focused single-column; calm surface; clear form/error styling |
| **Student** | Balanced density; clear primary action; subscription/notification entry without clutter |
| **Learning** | Comfortable reading measure; calm surfaces; progress without noise |
| **Assessment (live)** | Reduced chrome; high clarity for question/options/timer; touch-friendly targets |
| **Reader** | Immersive content; minimal chrome; readable width; toolbar secondary |
| **Subscription / Billing** | Clear plan comparison; honest Premium states; no fake urgency visuals |
| **Staff / Admin** | Higher density; table-first; compact controls; still accessible |
| **CMS / Editorial** | Workspace clarity; workflow status styling using approved states only |
| **Error / System** | Simple recovery; calm explanation; no decorative distraction |

Layouts select density and chrome; they do not invent palettes.

---

## 8. Component Styling Contracts

Aligned with [`14`](14-frontend-component-architecture.md):

| Contract | Requirement |
| --- | --- |
| Shared vocabulary | Buttons, fields, alerts, badges use one style language |
| Variant clarity | Primary / secondary / danger / ghost remain distinct |
| State completeness | Default, hover/focus (where applicable), disabled, loading, error, selected |
| Domain components | QuestionOption, ExamTimer, BookCard follow family rules without local palettes |
| No business styling | “Premium” appearance displays server entitlement state; does not grant access |
| Composition | Prefer composing primitives over one-off styled blocks |

Component styles must remain reusable across pages and templates.

---

## 9. Page & Template Styling Alignment

Every styled page/template must respect:

| Source | Constraint |
| --- | --- |
| [`15`](15-frontend-page-architecture.md) | One primary purpose; family density; state-complete presentation |
| [`16`](16-frontend-template-architecture.md) | Styles attach to layouts, sections, components, fragments—not ad-hoc page CSS islands |

Example conceptual mappings:

| Page | Styling composition |
| --- | --- |
| Student Dashboard | Student density + priority section spacing + progress/activity patterns |
| Exam Session | Assessment focus + timer/option clarity + reduced chrome |
| Book Reader | Reader measure + minimal toolbar + content primary |
| Admin Question Bank | Staff density + table/filter patterns |

---

## 10. State Styling Architecture

Conceptual visual treatment for states (not every surface needs every state):

| State | Styling intent |
| --- | --- |
| Loading | Skeleton/placeholder calm; avoid layout jump where practical |
| Empty | Helpful, non-alarming; clear next action |
| Validation error | Field-associated; Danger semantics + text |
| Permission denied | Clear, non-leaky; recovery action |
| Entitlement denied | Honest Premium/Locked; no dark-pattern urgency |
| Session expired | Clear re-auth path |
| Server error / Maintenance | Calm system messaging |
| Success | Success semantics + text/icon |
| Selected / Expanded | Clear affordance without relying on color alone |
| Locked / Free / Premium | Distinct, honest presentation |
| Pending / Completed / Failed | Status tokens + labels for billing/assessment |

Appearance reflects **server-provided** state only.

---

## 11. Assessment Styling Architecture

| Concern | Rule |
| --- | --- |
| Focus | Reduce competing chrome during live practice/exam |
| Timer | Highly legible; not decorative; accessible announcements conceptually supported |
| Options | Clear selection/focus; large enough touch targets |
| Correct / incorrect | Icon + text + color; never color-only |
| Progress | Calm, accurate representation of server progress |
| Exit protection UX | Clear, non-misleading |

Styles must not imply scores or completion the server has not provided.

---

## 12. Learning & Library Styling Architecture

| Surface | Styling priority |
| --- | --- |
| Course → Lesson hierarchy | Clear breadcrumb and hierarchical type scale |
| Lesson / material | Reading comfort; stable measure |
| Progress | Secondary to content; accurate |
| Library catalog | Scannable cards/list without card-overuse in marketing hero contexts |
| Reader | Content first; toolbar secondary; entitlement-aware locked states |

---

## 13. Staff / Admin Styling Architecture

| Concern | Rule |
| --- | --- |
| Density | Higher information density than student surfaces |
| Tables | Readable headers; zebra/divider language consistent; responsive collapse strategy conceptual |
| Queues | Status badges with labels; filter clarity |
| Bulk actions | Clear danger for destructive actions |
| Accessibility | Density never excuses missing focus or labels |

---

## 14. Responsive Styling Architecture

| Viewport | Styling behavior |
| --- | --- |
| Mobile | Single-column priority; compact nav; touch targets; readable lessons |
| Tablet | Adaptive columns where justified; assessment usable |
| Desktop | Wider learning layouts; staff density |
| Large desktop | Extra space without excessive line length |

Breakpoints as numeric implementation details are out of scope; behavior contracts are in scope.

---

## 15. Accessibility Styling Contract

| Requirement | Notes |
| --- | --- |
| Contrast | Text/surface and status combinations meet accessibility intent from docs/12 |
| Focus visibility | Never remove focus indication without equivalent |
| Non-color status | Icon and/or text with status colors |
| Target size | Touch-friendly where interaction is expected |
| Zoom / text resize | Layouts tolerate enlargement without trapping content |
| Reduced motion | Motion tokens degrade safely |

Styling supports accessibility; it does not replace semantic structure from templates.

---

## 16. Localization Styling Contract

| Requirement | Notes |
| --- | --- |
| Bangla + English | Font roles support both scripts |
| Text expansion | Buttons, nav, tables tolerate longer labels |
| Mixed content | Medical terms and mixed script remain readable |
| Dates / numbers / currency | Formatting is data-layer/presentation; styles must not clip localized strings |
| No English-width assumptions | Avoid fixed widths that break Bangla |

---

## 17. Premium / Freemium Styling Rules

Aligned with docs/11–12:

| Allowed | Forbidden |
| --- | --- |
| Clear Premium labeling | Fake scarcity countdown styling |
| Honest locked content states | Obscuring Free value |
| Calm upgrade CTAs | Manipulative urgency patterns |
| Distinct Premium accent role | Using Danger/Success to fake urgency |

Entitlement remains server-decided; styles only present the result.

---

## 18. Motion & Interaction Styling

| Prefer | Avoid |
| --- | --- |
| Short feedback on save/toggle | Continuous decorative animation |
| Disclosure/accordion clarity | Motion that hides errors |
| Exam-safe minimal motion | Distracting timer animations |

Honor reduced-motion preferences conceptually.

---

## 19. Asset & Media Styling

| Asset type | Styling concern |
| --- | --- |
| Logos / brand marks | Consistent sizing in chrome; brand-first on public heroes |
| Icons | Aligned optical sizes; paired with text for status |
| Course / book imagery | Aspect stability; no layout jump; alt text is content responsibility |
| CMS media | Responsive containment; do not break reading measure |
| Question images | Clear, accessible presentation within assessment layout |

Storage and CDN configuration are out of scope.

---

## 20. HTMX & Alpine Styling Boundaries

| Enhancement | Styling rule |
| --- | --- |
| HTMX fragments | Fragments must reuse the same token/component styles as full pages |
| Partial swaps | Avoid style flash from inconsistent class languages |
| Alpine local UI | Visibility/disclosure only; no alternate “authorized” look client-side |
| Loading indicators | Consistent with system feedback styling |

Client enhancements must not invent temporary entitlement or success visuals that contradict server truth (especially payments).

---

## 21. Custom CSS Boundary

| Prefer | When custom CSS may be considered (future implementation) |
| --- | --- |
| Token-mapped utilities | Truly unavailable utility expression for a **system-wide** need |
| Shared component contracts | Print/reader edge cases approved under governance |
| | Third-party embed containment that utilities cannot isolate cleanly |

| Custom CSS must not |
| --- |
| Introduce page-local palettes |
| Encode business rules |
| Duplicate design-system concepts under new names |
| Bypass accessibility focus/contrast rules |

---

## 22. Conceptual Style Organization

Conceptual areas only (not a command to create files now):

```text
styles/   (conceptual)
  tokens/     → semantic token definitions (future)
  base/       → document defaults aligned to design system
  layouts/    → family density helpers if needed
  components/ → shared component style contracts if needed beyond utilities
  utilities/  → rare project-specific utilities
  print/      → optional future print/reader aids
```

Templates remain the primary composition surface; styles support them.

---

## 23. Naming Conventions

Conceptual names should mirror design-system roles and component vocabulary.

| Good conceptual names | Avoid |
| --- | --- |
| color.primary, surface.elevated, text.muted, status.danger, space.section, type.page-title, radius.control, motion.short | blue2, boxShadowFancy, tempRed, studentGreen, finalSpacing |

Names must remain stable and semantic.

---

## 24. Dependency & Reuse Rules

Allowed conceptual direction:

```text
Design tokens → Utilities/theme → Primitives → Components → Sections → Pages
```

| Rule |
| --- |
| Pages must not define private token systems |
| Components must not depend on page-specific styles |
| Assessment styles must not depend on billing styles |
| Public marketing styles must not require authenticated chrome |
| Shared styles remain domain-light |

Before adding a new style pattern: search existing tokens/components; compose; extend only if semantics stay coherent; avoid duplicates.

---

## 25. Business-Logic Boundary for Styling

| Styles may | Styles must not |
| --- | --- |
| Present server-provided Free/Premium/Locked | Decide entitlement |
| Present role-aware chrome visibility already decided by server | Calculate RBAC |
| Style correct/incorrect feedback provided by server | Score attempts |
| Style payment pending/success/failure from server | Confirm payments |
| Emphasize primary CTAs | Encode workflow transitions |

---

## 26. Security-Aware Styling

| Concern | Rule |
| --- | --- |
| Error presentation | No stack traces, tokens, paths, or secrets in styled messages |
| Auth forms | Clear errors without user enumeration styling tricks that leak policy beyond server messaging |
| Sensitive actions | Re-auth screens remain focused and calm |
| Hidden content | Do not style “peek” of locked premium body content |

Styles are never a security boundary.

---

## 27. Performance Styling Architecture

| Guidance |
| --- |
| Prefer utility reuse over large one-off CSS |
| Avoid unused custom sheets |
| Keep assessment pages visually light |
| Optimize media presentation without sacrificing clarity |
| Avoid excessive decorative layers |

Correctness, accessibility, and security outrank micro-optimization.

---

## 28. Styling Testing Strategy

Conceptual tests: design-system alignment; contrast/focus; responsive density; localization expansion; component variant consistency; assessment readability; reader measure; Free/Premium honesty; reduced motion; regression against visual drift.

Complements: component, page, template, and accessibility tests.

---

## 29. Styling Documentation Expectations

Future implementation should document (later): token catalog; theme mapping notes; component style variants; family density rules; known exceptions; accessibility checks.

Do not create implementation style docs or config files now.

---

## 30. Future Styling Extensions

**Future-only:** dark mode token set; Flutter theme bridge; advanced visualization palettes; Offline Mode UI variants; Institution Portal branding layers; AI Tutor surfaces; Adaptive Learning visualizations.

Must not silently become V1 requirements. Dark mode is explicitly Future-only unless a later gate approves it.

---

## 31. Styling Governance

| Concern | Rule |
| --- | --- |
| Ownership | Styling changes align with design-system ownership |
| Reviews | UX, design-system, accessibility, and frontend-architecture review for material changes |
| Drift control | No unofficial palettes or type scales |
| Breaking changes | Require justification and migration notes |
| Deprecation | Remove obsolete style patterns safely |
| New families | Require justification against docs/12–16 |

---

## 32. Cross References

| Document | Use |
| --- | --- |
| [`11`](11-ui-ux-specification.md) | Experience & IA expectations |
| [`12`](12-design-system.md) | Authoritative visual language |
| [`13`](13-frontend-architecture.md) | Tailwind direction & frontend boundaries |
| [`14`](14-frontend-component-architecture.md) | Component style contracts |
| [`15`](15-frontend-page-architecture.md) | Page family density & composition |
| [`16`](16-frontend-template-architecture.md) | Template attachment points |
| [`03`](03-user-roles.md) | Role-aware presentation only |
| [`07`](07-security-and-session-management.md) | Security-safe presentation |
| [`09`](09-business-rules.md) | Entitlement/workflow truth remains server-side |
| [`10`](10-development-roadmap.md) | Delivery scope |

**This document does not modify any approved document.**

---

## 33. Acceptance Criteria

This document is acceptable when:

1. Styling architecture principles and layer model are defined  
2. Technology direction (Tailwind-first, minimal custom CSS) is defined  
3. Semantic token architecture is defined without hex/CSS/Tailwind class source  
4. Design-system → styling mapping is defined  
5. Layout family, component, page/template alignment is defined  
6. State, assessment, learning/library, and staff styling rules are defined  
7. Responsive, accessibility, localization, premium, and motion contracts are defined  
8. Asset, HTMX/Alpine, and custom CSS boundaries are defined  
9. Conceptual organization, naming, dependency, and reuse rules are defined  
10. Business-logic and security-aware styling boundaries are defined  
11. Performance, testing, documentation expectations, governance, and Future-only extensions are defined  
12. **No** CSS, Tailwind classes, theme config, HTML, JS, templates, or Python is generated  
13. Docs `00`–`16` remain unchanged  

---

## 34. Document Lock

**Status:** `docs/17-frontend-styling-architecture.md` is **Approved v1.0.0 — LOCKED**.

This document is the authoritative conceptual styling architecture for Nursilo V1. Substantive content remains unchanged. Docs `00`–`16` remain unmodified. Next documentation proceeds only when explicitly requested. Implementation artifacts are not generated unless requested in a separate gate.

---

*Nursilo — Learn. Practice. Succeed.*
