# Nursilo — API Design

| Field | Value |
| --- | --- |
| Document | `08-api-design.md` |
| Version | `1.0.0` |
| Status | **Approved** — locked API design specification |
| Product | Nursilo |
| Depends on | [`00-project-vision.md`](00-project-vision.md) … [`07-security-and-session-management.md`](07-security-and-session-management.md) (Approved / gated docs **unchanged** by this document) |
| Purpose | Conceptual API standards and design principles for future REST APIs |
| Out of scope | Endpoint catalog; payloads; code; serializers; views; URL routes; Swagger; OpenAPI; database; ORM; migrations |
| Nature | **Additive only** — does not modify locked docs `00`–`07` |
| Next gated doc | `09-development-roadmap.md` |

---

## 1. Purpose

This document defines the **API contract philosophy** for Nursilo. It establishes how future HTTP APIs must behave so web (Templates/HTMX), Flutter, and later integrations share one consistent surface.

It defines:

- API philosophy  
- API lifecycle  
- Standards and consistency rules  
- Versioning  
- Authentication strategy (conceptual)  
- Authorization layering  
- Error conventions  
- Cross-cutting concerns (pagination, filtering, idempotency, rate limiting, security, localization)

It does **NOT** define:

- Endpoint lists or URI paths  
- Request/response payloads  
- OpenAPI / Swagger specifications  
- Django views, DRF serializers, or authentication code  
- Database schemas or migrations  

This document is the governing standard for all future API work. Implementation details follow only after this philosophy is approved and subsequent gated docs request them.

---

## 2. API Design Principles

| Principle | Meaning for Nursilo |
| --- | --- |
| **API First** | Domain capabilities are designed for reuse by multiple clients; Templates are one adapter, not the sole consumer |
| **Resource-oriented** | APIs expose stable business resources, not database tables or template pages |
| **Consistency** | Naming, errors, auth, pagination, and status semantics stay uniform across resources |
| **Predictability** | Clients can infer behavior from conventions without special cases per feature |
| **Stateless requests** | Each request carries the credentials/context needed for authorization; server does not rely on hidden client-only state for authZ |
| **Secure by default** | Deny by default; HTTPS; layered authN/authZ; no sensitive leakage in errors |
| **Backward compatibility** | Prefer additive evolution within a version |
| **Minimal breaking changes** | Breaking changes require a new API version and deprecation process |
| **Separation from presentation** | APIs must not encode HTMX partials, template structure, or UI chrome |
| **Service-layer driven** | All mutations and privileged reads go through domain services |
| **Future mobile ready** | Same services and rules serve Flutter without a second business model |
| **Future AI ready** | Structured, versioned resources and errors support later AI tutor / adaptive clients as additional adapters |

---

## 3. API Architecture

Conceptual request flow:

```text
Flutter
Templates
HTMX
Future integrations
        │
        ▼
   API Adapter
   (HTTP / future protocol boundary)
        │
        ▼
   Service Layer
   (Exam, Entitlement, Editorial, Billing, …)
        │
        ▼
   Repositories
        │
        ▼
   Database / media ports
```

| Rule | Specification |
| --- | --- |
| No bypass | APIs **never** bypass the service layer to reach repositories or persistence directly |
| Shared rules | Entitlements, RBAC, scoring, publish state, and session/security policies are identical for Templates and API adapters |
| Adapter role | The API adapter authenticates, validates input shape at the boundary, calls services, and maps domain results/errors to HTTP |

This aligns with the dependency rule in [`04-system-architecture.md`](04-system-architecture.md): Presentation → Services → Repositories → Persistence.

---

## 4. Versioning Strategy

| Item | Specification |
| --- | --- |
| **Current version** | **v1** |
| **Future** | **v2** (and later) when breaking changes are required |

| Rule | Specification |
| --- | --- |
| Style | **URI versioning** (version appears in the resource path namespace) |
| Breaking changes | Require a **new** major API version |
| Additive changes | Remain in the **same** version when backward compatible |
| Deprecation | Obsolete behavior is announced and marked deprecated before removal (see §19) |
| Sunset | Deprecated versions/behaviors are retired on a published schedule after a grace period |

Clients must not assume undocumented fields or side effects remain stable.

---

## 5. Authentication Strategy

Conceptual only—no authentication code or token formats in this document.

| Phase | Approach |
| --- | --- |
| **V1 (web)** | Session authentication for browser clients (Templates / HTMX), consistent with [`07-security-and-session-management.md`](07-security-and-session-management.md) |
| **Future** | Bearer tokens for programmatic / mobile clients |
| **Future** | OAuth |
| **Future** | SSO (as reserved in security docs) |
| **Future** | Mobile tokens for Flutter |

| Clarification | Specification |
| --- | --- |
| Separation | **Authentication** establishes identity; **authorization** decides allow/deny |
| Single model | Future token/SSO adapters must feed the same identity into RBAC + entitlements—not a parallel permission system |
| Session security | Concurrent session caps, revocation, and timeouts from doc `07` apply to session-authenticated clients |

---

## 6. Authorization

Every privileged API request is evaluated through layered checks:

```text
Authentication
    ↓
RBAC
    ↓
Entitlements
    ↓
Domain Policy
    ↓
Allow / Deny  (fail closed)
```

| Layer | Defined primarily in |
| --- | --- |
| RBAC | [`03-user-roles.md`](03-user-roles.md) |
| Entitlements (Free/Premium) | Vision / requirements / architecture / domain model |
| Domain policy | Editorial state, attempt lifecycle, ownership, publish visibility |
| Enforcement | Service layer ([`04-system-architecture.md`](04-system-architecture.md)); not the API adapter alone |

API adapters must not grant access that services would deny.

---

## 7. Resource Design

Conceptual resources represent business aggregates and catalogs—not ORM rows.

| Example resource families | Intent |
| --- | --- |
| Questions | Assessment catalog identity and published views |
| Attempts | Practice/exam runtime |
| Books | Library catalog and entitled access |
| Courses / Lessons | Learning hierarchy consumption |
| Users | Account/profile surfaces appropriate to role |
| Subscriptions | Plan/entitlement status |
| Notifications | In-app notification resources |
| CMS | Public content surfaces |

| Rule | Specification |
| --- | --- |
| Encapsulation | Never expose internal persistence structures, join tables, or storage keys as the public contract |
| Aggregate honesty | Resources should reflect domain aggregates and read models from [`05-domain-model.md`](05-domain-model.md) |
| Soft delete / archive | Learner-facing resources omit archived/unpublished content unless staff preview policies apply |

This document does not enumerate endpoints for these resources.

---

## 8. Standard HTTP Concepts

Conceptual verb usage (no routes or payloads):

| Method | Conceptual use |
| --- | --- |
| **GET** | Safe, idempotent retrieval |
| **POST** | Create resources or trigger non-idempotent actions (where appropriate) |
| **PUT** | Full replacement of a replaceable resource representation |
| **PATCH** | Partial update of a resource |
| **DELETE** | Removal or archive semantics as domain policy defines (prefer soft delete for educational content) |

HTTP semantics must match domain intent. Side effects belong in services, not in opportunistic GET handlers.

---

## 9. Error Handling Philosophy

| Expectation | Specification |
| --- | --- |
| Consistency | Errors follow one shape/convention across the API |
| Localization | User-facing messages support Bangla and English |
| Machine-readable codes | Stable error codes for client branching |
| No sensitive leakage | No secrets, tokens, password hashes, or internal paths |
| No stack traces | Stack traces never appear in client responses |
| Validation errors | Clear field/constraint failures |
| Authentication errors | Unauthenticated or invalid session/token |
| Authorization errors | Authenticated but forbidden (RBAC/entitlement/policy) |
| Business rule violations | Domain refusals (workflow illegal, attempt not resumable, free-tier cap, etc.) |

Errors are mapped from domain/service outcomes at the adapter boundary.

---

## 10. Pagination

Conceptual support:

| Style | Timing |
| --- | --- |
| Page-based pagination | V1 expectation for list resources |
| Cursor-based pagination | **Future** for high-volume feeds |
| Metadata | Page/cursor metadata accompanies collections (conceptual; no payload schema here) |

Unbounded list dumps are discouraged for learner and admin list resources.

---

## 11. Filtering

Conceptual query capabilities (Future maturity may deepen):

| Capability | Intent |
| --- | --- |
| Filtering | Narrow collections by domain attributes |
| Sorting | Stable, documented sort keys |
| Searching | Text search aligned with search architecture |
| Field selection | **Future** — reduce payload surface |
| Expansion | **Future** — controlled inclusion of related resources |

Filtering must not become a backdoor past entitlements or publish rules.

---

## 12. Idempotency

| Concern | Specification |
| --- | --- |
| Safe retries | Clients may retry safely where operations are designed to be idempotent |
| Payments | Payment confirmation and entitlement activation must tolerate duplicate gateway signals without duplicate harmful effects |
| Webhooks | Future webhook receivers verify authenticity and apply idempotent handling |
| No duplicate effects | Confirmed business outcomes (premium grant, attempt submit) must not double-apply on replay |

Aligns with billing and transaction strategy in architecture docs.

---

## 13. Rate Limiting

Conceptual limits may apply differently to:

| Audience |
| --- |
| Anonymous users |
| Authenticated users |
| Admins |
| Integrations |
| Future public APIs |

| Concern | Specification |
| --- | --- |
| Abuse control | Protect auth, search, and write-heavy resources |
| **429** | Clients should treat rate-limit responses as temporary; retry with backoff conceptually |
| Configuration | Thresholds are operational policy (no config examples here) |

Complements login throttling in [`07-security-and-session-management.md`](07-security-and-session-management.md).

---

## 14. File Uploads

Conceptual upload domains:

| Asset class |
| --- |
| Books |
| Question images |
| CMS media |
| Profile photos |
| Future videos |

| Rule | Specification |
| --- | --- |
| Mediation | Services validate identity, RBAC, entitlements, and content policy before accepting or serving files |
| Access | Controlled delivery remains entitlement-aware (architecture media access rules) |
| Storage | Storage keys are not a public authorization mechanism |

---

## 15. Webhooks

**Future only.**

| Topic | Intent |
| --- | --- |
| Payments | Gateway confirmation callbacks |
| Notifications | Future outbound/inbound notification hooks |
| Integrations | Partner and institutional systems |
| Idempotency | Mandatory for receivers |
| Verification | Authenticity checks before state changes |

Webhooks call the same Billing / Notification services—never raw table updates.

---

## 16. API Security

This section references [`07-security-and-session-management.md`](07-security-and-session-management.md) and architecture secure-HTTP guidance.

| Control | API expectation |
| --- | --- |
| HTTPS | Required in production |
| Authentication | Session (V1 web); future tokens/SSO/mobile |
| Authorization | RBAC + entitlements + domain policy |
| CSRF | Required for cookie/session authenticated state-changing requests; HTMX included |
| Future token auth | Bearer/mobile tokens without weakening service checks |
| Rate limiting | As §13 |
| Input validation | Boundary validation before services |
| Output encoding | Safe representation; no reflected injection vectors |
| Audit logging | Security and privileged business events per prior docs |

---

## 17. Performance

Conceptual expectations:

| Concern | Intent |
| --- | --- |
| Caching | Cache public/safe GETs carefully; never cache personalized entitlement decisions unsafely |
| Compression | Transport compression where appropriate |
| Pagination | Required discipline for large collections |
| Efficient payloads | Avoid over-fetching; future field selection may help |
| Search optimization | Align with search projection architecture |
| Future CDN | Public CMS/static assets at the edge |

Correctness and security outrank premature optimization.

---

## 18. Localization

| Concern | Specification |
| --- | --- |
| Languages | Bangla and English |
| Negotiation | Locale preference via user profile and/or request locale conventions |
| Errors | Localized user-facing error messages |
| Content | Localized catalog content follows multilingual strategy (no duplicated domain tables) |

API localization must not fork authorization rules by language.

---

## 19. Deprecation Policy

| Stage | Expectation |
| --- | --- |
| Announcement | Breaking or retiring behavior is announced to stakeholders/clients |
| Grace period | Deprecated version/behavior remains available for a defined period |
| Migration guidance | Document how clients should move forward (conceptual guidance, not endpoint catalogs here) |
| Removal schedule | Sunset date communicated; then retired |

Silent breaking changes within `v1` are not permitted.

---

## 20. API Lifecycle

Conceptual lifecycle for any API capability:

```text
Design
  → Review
  → Implement
  → Test
  → Release
  → Monitor
  → Deprecate
  → Retire
```

| Stage | Intent |
| --- | --- |
| Design | Align with this philosophy + domain model |
| Review | Architecture/security/product gate |
| Implement | Service-layer first; adapter second |
| Test | AuthZ, entitlements, idempotency, errors |
| Release | Versioned, observable |
| Monitor | Errors, latency, abuse |
| Deprecate / Retire | Per §19 |

---

## 21. Future Integrations

Reserved consumers / surfaces (not V1 endpoint catalogs):

| Integration |
| --- |
| Flutter |
| Desktop |
| AI Tutor |
| Institution Portal |
| Partner APIs |
| Third-party LMS |
| Public API |

All must reuse Nursilo services, RBAC, entitlements, and session/token policies—not parallel business logic.

---

## 22. Cross References

| Document | Consistency expectation |
| --- | --- |
| [`03-user-roles.md`](03-user-roles.md) | API authZ mirrors RBAC matrices |
| [`04-system-architecture.md`](04-system-architecture.md) | Adapter → service → repository dependency rule |
| [`05-domain-model.md`](05-domain-model.md) | Resources reflect aggregates and invariants |
| [`06-database-design.md`](06-database-design.md) | Persistence remains internal; APIs do not expose schema |
| [`07-security-and-session-management.md`](07-security-and-session-management.md) | Session/token security, CSRF, rate limits, audit events |

This API design document does **not** modify those documents.

---

## 23. Acceptance Criteria

This document is acceptable when:

1. API philosophy and principles are defined  
2. Versioning strategy exists (`v1` / future `v2`, URI versioning, additive vs breaking)  
3. Authentication and authorization are clearly separated and layered  
4. Error handling philosophy is standardized  
5. Pagination and filtering concepts exist (without payloads)  
6. Idempotency, rate limiting, uploads, and future webhooks are addressed conceptually  
7. Security principles reference doc `07` and architecture  
8. Localization and deprecation/lifecycle are documented  
9. Future integrations are reserved  
10. **No** endpoint catalogs exist  
11. **No** request/response payloads exist  
12. **No** OpenAPI/Swagger, code, serializers, views, routes, SQL, ORM, or migrations exist  
13. Locked documents `00`–`07` remain unmodified  

---

## 24. Document Lock

**Status:** `docs/08-api-design.md` is **Approved** and locked at **Version 1.0.0**.

Locked documents `docs/00`–`docs/07` remain unmodified. Next documentation proceeds only when explicitly requested. No endpoint catalogs, OpenAPI/Swagger, or implementation artifacts will be generated until separately requested.

---

*Nursilo — Learn. Practice. Succeed.*
