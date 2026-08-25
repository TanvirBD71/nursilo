# Nursilo — Development Roadmap

| Field | Value |
| --- | --- |
| Document | `10-development-roadmap.md` |
| Version | `1.0.0` |
| Status | **Approved** — locked development roadmap |
| Product | Nursilo |
| Depends on | [`00`](00-project-vision.md)–[`09`](09-business-rules.md) (all Approved v1.0.0; **unchanged** by this document) |
| Purpose | Authoritative development roadmap from MVP through future releases |
| Out of scope | Source code; Django models; ORM; SQL; migrations; API implementation; UI implementation; sprint task details; Git workflow; CI/CD configuration |
| Nature | **Additive only** — does not modify locked docs `00`–`09` |

---

## 1. Purpose

This document defines the **strategic implementation roadmap** for Nursilo.

It specifies:

- **WHAT** should be built  
- **WHEN** it should be built  
- **WHY** that sequence exists  

It does **not** describe **HOW** features are implemented. It governs **implementation sequencing**—not implementation itself.

Engineering, product, and QA use this roadmap to align delivery with approved architecture ([`04`](04-system-architecture.md)), domain model ([`05`](05-domain-model.md)), security ([`07`](07-security-and-session-management.md)), API philosophy ([`08`](08-api-design.md)), business rules ([`09`](09-business-rules.md)), and the product backlog ([`02`](02-feature-list.md)).

---

## 2. Roadmap Principles

| Principle | Meaning |
| --- | --- |
| **Build foundations first** | Identity, RBAC, persistence posture, security, and service boundaries precede features |
| **Core domains before supporting domains** | Assessment System and entitlements precede secondary surfaces |
| **API-first architecture** | Business rules live in services reusable by Templates and future Flutter/API adapters |
| **Security first** | AuthN/session/RBAC controls ship before public content and payments |
| **Stable milestones** | Each phase ends in a reviewable, testable increment |
| **Backward compatibility** | Preserve attempt history, question versions, and entitlement integrity across releases |
| **Minimize technical debt** | Prefer simple modular monolith patterns; defer Redis/Celery/R2 until justified |
| **Incremental delivery** | Ship thin vertical slices after foundations; avoid big-bang launches |

---

## 3. Overall Development Strategy

| Stage | Intent |
| --- | --- |
| **Foundation** | Project skeleton, accounts, RBAC, security sessions, settings, audit, service layer conventions |
| **Core Platform** | Learning hierarchy, editorial workflow, Question Bank, attempt runtime primitives |
| **MVP** | Learner can register, learn, practice, take exams, review, see basic progress under freemium rules (payments may be staged) |
| **Public Release** | Polished V1.0: library, CMS/SEO, search, notifications, subscriptions/payments, production hardening |
| **Post-MVP** | V1.1/V1.2 quality, analytics depth, bulk ops maturity, API surface for mobile prep |
| **Future Expansion** | AI tutor, adaptive learning, Flutter, institutions, offline/PWA, advanced tooling |

Assessment remains the product core; learning content exists to support exam success—not certificates.

---

## 4. Development Phases

### Phase 1 — Foundation

| Focus | Includes (examples) |
| --- | --- |
| Platform skeleton | Modular Django apps, settings split, PostgreSQL connectivity, Passenger-ready posture |
| Authentication | Registration, login/logout, password reset, email verification |
| Sessions & security | Concurrent session cap (3), device list basics, idle/absolute timeouts, audit of security events |
| RBAC | Roles and least-privilege enforcement |
| Core architecture | Service layer conventions, fail-closed authZ, logging/audit foundations |
| Database | Schema aligned to approved design for identity, roles, settings, audit |
| Configuration | SettingsService concepts, feature toggles, freemium cap configuration hooks |

**Exit intent:** A secure identity and authorization base exists; no learner content required yet.

### Phase 2 — Learning, Assessment Catalog, Editorial

| Focus | Includes (examples) |
| --- | --- |
| Learning hierarchy | Course → … → Lesson → Learning Material |
| Editorial workflow | Draft → Review → Approved → Published → Archived; staff preview |
| Question Bank | Types, difficulty, metadata, M:N topics, versioning strategy, soft delete |
| Multilingual content | Bangla/English without duplicated domain tables |
| Staff admin surfaces | Content authoring for Authors/Reviewers/Editors |

**Exit intent:** Published learning objects and questions can exist under workflow control.

### Phase 3 — Practice, Exams, Review, Analytics

| Focus | Includes (examples) |
| --- | --- |
| Practice | Topic/chapter/subject/random/custom; free-tier caps |
| Exams | Timed exams, mocks, resume interrupted exam, auto-submit, permanent attempt history |
| Review | Wrong answers, bookmarks, explanations per policy |
| Analytics | Weak/strong topics, basic progress; premium gating hooks for advanced analytics |
| Integrity | Attempt items freeze question versions |

**Exit intent:** The Assessment System core loop works end-to-end for entitled learners.

### Phase 4 — Library, CMS, Search, Notifications

| Focus | Includes (examples) |
| --- | --- |
| Library | Multi-format books, entitlement-aware read/download |
| CMS & blog | Public pages, SEO, contact/feedback |
| Search | Global search across courses, books, lessons, questions, authors; publish + entitlement filters |
| Notifications | In-app notifications, announcements, security notifications |

**Exit intent:** Discovery, content marketing, and engagement surfaces support a public product.

### Phase 5 — Subscriptions, Payments, Premium

| Focus | Includes (examples) |
| --- | --- |
| Entitlements | Central Free vs Premium capability evaluation |
| Subscriptions | Lifecycle states; dashboard status |
| Payments | bKash / Nagad / SSLCommerz when enabled; verification; idempotency |
| Premium unlocks | Full bank, unlimited mocks, tracks, premium books, advanced analytics |
| Manual grant | Audited Admin/Super Admin support path |

**Exit intent:** Freemium monetization is enforceable and auditable.

### Phase 6 — Optimization, Performance, Caching, Logging, QA

| Focus | Includes (examples) |
| --- | --- |
| Performance | Query discipline, pagination, published-content partial-index usage |
| Caching | Conceptual CDN/public page caching; careful entitlement cache invalidation |
| Logging & ops | Error logging, audit access, production checklist |
| QA hardening | Regression packs, security review, load sanity for attempts/payments |
| Bulk ops maturity | Import/export reliability for large question volumes |

**Exit intent:** V1 public release is production-ready on cPanel Passenger + Cloudflare + PostgreSQL.

---

## 5. MVP Scope

### 5.1 In MVP

| Area | MVP includes |
| --- | --- |
| Accounts | Register, verify email, login, profile + academic profile, password reset |
| Security | Session policy (3 devices), basic device logout, lockout/throttle essentials |
| RBAC | Staff roles operational for content pipeline |
| Learning | Browse/publish hierarchy; Continue Learning; progress |
| Assessment | Question Bank + practice + exams + resume + review wrong/bookmarks |
| Freemium | Entitlement checks with configurable free practice caps |
| Dashboard | Core widgets (continue, progress, exam history, streak basics, subscription status placeholder) |
| Admin | Content + question management, editorial, audit of critical actions |

### 5.2 May be staged at MVP edge (still V1.0 target)

| Area | Note |
| --- | --- |
| Live payment gateways | Entitlement model required in MVP; gateway go-live may follow content readiness |
| Full library formats | At least one entitled read path; remaining formats complete toward V1.0 |
| Advanced Chart.js analytics | Basic progress in MVP; richer charts toward V1.0/V1.1 |
| Global search depth | Basic search acceptable for MVP; bilingual competence improves in V1.1 |

### 5.3 Explicitly out of MVP

| Out |
| --- |
| Certificates |
| Institutional tenancy |
| AI tutor / adaptive learning product features |
| Flutter apps / PWA offline |
| Question discussion |
| Redis/Celery/R2 as required infrastructure |
| SSO / MFA product features |

---

## 6. Version Planning

| Version | Focus |
| --- | --- |
| **V1.0** | Public Bangladesh-first freemium web platform: Assessment core, learning, library, CMS/SEO, search, notifications, subscriptions/payments, production security posture |
| **V1.1** | Quality and depth: saved custom exam templates, chart visualizations, bilingual search competence, duplicate detection, content/question usage analytics, email notifications maturity, API versioned surface prep |
| **V1.2** | Hardening and scale prep: performance, reporting polish, bulk content operations excellence, operational runbooks |
| **V2.0** | Major capability expansion candidate (mobile-first API maturity, richer personalization foundations)—only after V1 stability |
| **Future** | AI tutor, adaptive learning, Flutter, institution portal, offline/PWA, OSCE/procedures/flashcards/calculators, media library, international payments |

Versions must not break historical attempt integrity or entitlement audit trails.

---

## 7. Feature Dependencies

```text
Authentication
    → Sessions / Security
        → RBAC
            → Editorial Workflow
                → Learning Catalog
                    → Question Bank (versioned)
                        → Practice / Exam Runtime
                            → Review
                                → Analytics
Billing / Entitlements ─────────────────────────────→ Premium gates (practice, exams, library, analytics)
CMS / Library / Search / Notifications ← after publishable catalog exists
Payments ← after Entitlements skeleton exists
```

| Dependency | Why |
| --- | --- |
| Authentication before RBAC | Roles attach to identities |
| RBAC before Editorial | Approve/Publish require role checks |
| Editorial before Learning (learner-facing) | Only Published content is visible |
| Learning before Assessment targeting | Topic/chapter/subject scopes need hierarchy |
| Assessment catalog before Practice/Exams | No attempts without questions/versions |
| Assessment runtime before Analytics | Stats derive from attempts |
| Entitlements before Premium enforcement | Capabilities must be central |
| Billing before paid Premium activation | Verified payment or audited grant only |
| Publish events before Search projections | Index is not source of truth |

---

## 8. Release Gates

No phase advances to “done” without:

| Gate | Requirement |
| --- | --- |
| Architecture alignment | Matches approved architecture and dependency rule |
| Business rules alignment | Matches [`09-business-rules.md`](09-business-rules.md) |
| QA | Phase test pack executed (see §10) |
| Documentation | Phase notes / operator awareness as needed; no silent contradiction of locked docs |
| Approval | Product/architecture acceptance of the milestone |

Skipping gates to “ship faster” is not permitted for production releases.

---

## 9. Documentation Gates

Implementation **cannot bypass** documentation approval.

| Doc | Status |
| --- | --- |
| `00` Project Vision | Approved v1.0.0 |
| `01` System Requirements | Approved v1.0.0 |
| `02` Feature List | Approved v1.0.0 |
| `03` User Roles | Approved v1.0.0 |
| `04` System Architecture | Approved v1.0.0 |
| `05` Domain Model | Approved v1.0.0 |
| `06` Database Design | Approved v1.0.0 |
| `07` Security & Sessions | Approved v1.0.0 |
| `08` API Design | Approved v1.0.0 |
| `09` Business Rules | Approved v1.0.0 |
| `10` Development Roadmap | Draft (this document) |

Further docs (UI, coding standards, deployment, etc.) proceed only when requested and approved. Code generation for a domain should not begin until that domain’s governing docs are approved and the relevant roadmap phase is authorized.

---

## 10. Testing Strategy

Conceptual layers (no tooling prescriptions):

| Layer | Intent |
| --- | --- |
| **Unit testing** | Service-level rules (entitlements, scoring, workflow transitions, session policy) |
| **Integration testing** | Multi-service flows (publish → search projection; payment confirm → entitlement) |
| **Security testing** | AuthN/session cap, CSRF posture, entitlement bypass attempts, RBAC denials |
| **Performance testing** | Attempt submit, catalog browse, search under expected V1 load |
| **Acceptance testing** | MVP and V1.0 scenarios against business rules and backlog acceptance criteria |
| **Regression testing** | Protect attempt integrity, versioning, and freemium gates across releases |

---

## 11. Quality Assurance Strategy

| Review | Focus |
| --- | --- |
| **Code quality** | Clarity, modularity, Django best practices (when coding begins) |
| **Architecture review** | Service boundaries; no business rules in templates |
| **Security review** | Against docs `07` and `09` security/account rules |
| **Performance review** | Query patterns, pagination, published filters |
| **Documentation review** | Delivery matches locked specs; gaps filed as doc/change requests—not silent drift |

---

## 12. Risk Management

| Risk | Mitigation |
| --- | --- |
| Building UI before services | Enforce service-first sequencing in Phases 1–3 |
| Payment complexity delaying learning value | Ship entitlement skeleton early; enable gateways when content-ready |
| Question volume / import quality | Prioritize bulk import/export and duplicate detection in V1/V1.1 |
| Scope creep (AI, Flutter, institutions) | Keep Future explicitly gated; protect MVP |
| Technical debt (rules in templates) | Architecture + code review gates |
| Breaking historical attempts | Versioning + migration safety rules from docs `05`/`06`/`09` |
| Credential sharing / abuse | Session cap, credential sharing policy, audit, support playbooks |
| Dependency delays (gateway accounts, content) | Parallelize content ops with Phase 2–3 engineering |

---

## 13. Future Roadmap

| Theme | Timing |
| --- | --- |
| AI Tutor | Future (AI-ready data preserved in V1) |
| Adaptive Learning | Future |
| Flutter Android/iOS | Future (after API-first maturity) |
| Institution Portal | Future (post product-market fit) |
| Offline / PWA | Future |
| Advanced Analytics | Deepen in V1.1+; AI-driven later |
| OSCE / procedures / flashcards / calculators | Future |
| Central media library | Future |
| SSO / MFA | Future (security doc reservations) |

Future items must not dilute Phases 1–6 or V1.0 scope.

---

## 14. Success Metrics

| Metric class | Examples |
| --- | --- |
| **Development completion** | Phases closed against gates |
| **Feature completeness** | MVP/V1.0 backlog Must items delivered |
| **Performance** | Interactive learner flows acceptable on target hosting |
| **Reliability** | Attempt submit and payment confirmation correctness/idempotency |
| **Security** | Session/RBAC/entitlement bypass tests fail closed |
| **Maintainability** | Clear app boundaries; low rule duplication; docs still authoritative |

Product metrics (conversion, retention) remain guided by vision/requirements; this roadmap measures delivery readiness.

---

## 15. Cross References

| Document | Use in roadmap |
| --- | --- |
| [`00`](00-project-vision.md)–[`02`](02-feature-list.md) | Scope, backlog, freemium intent |
| [`03`](03-user-roles.md) | RBAC sequencing |
| [`04`](04-system-architecture.md) | Service/API-first delivery shape |
| [`05`](05-domain-model.md)–[`06`](06-database-design.md) | Data integrity sequencing |
| [`07`](07-security-and-session-management.md) | Security-first foundation |
| [`08`](08-api-design.md) | Future API/mobile readiness without early endpoint sprawl |
| [`09`](09-business-rules.md) | Behavioral acceptance for every phase |

This roadmap does **not** modify docs `00`–`09`.

---

## 16. Acceptance Criteria

This roadmap is acceptable when:

1. Development phases are clearly defined (Foundation through Optimization)  
2. MVP scope is defined (in / staged / out)  
3. Version planning exists (V1.0–V2.0 + Future)  
4. Feature dependencies are documented  
5. Release gates and documentation gates exist  
6. Testing and QA strategies are defined conceptually  
7. Risks and future roadmap are acknowledged without expanding V1 scope  
8. **No** implementation details, code, database schema DDL, API implementation, UI implementation, sprint tasks, Git, or CI/CD config exist  
9. Locked documents `00`–`09` remain unmodified  

---

## 17. Document Lock

**Status:** `docs/10-development-roadmap.md` is **Approved** and locked at **Version 1.0.0**.

Locked documents `docs/00`–`docs/09` remain unmodified. Next documentation proceeds only when explicitly requested. No implementation artifacts will be generated until separately requested.

---

*Nursilo — Learn. Practice. Succeed.*
