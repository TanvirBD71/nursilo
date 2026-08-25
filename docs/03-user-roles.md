# Nursilo — User Roles & RBAC Specification

| Field | Value |
| --- | --- |
| Document | `03-user-roles.md` |
| Version | `1.0.0` |
| Status | **Approved** — locked RBAC specification |
| Product | Nursilo |
| Depends on | [`00-project-vision.md`](00-project-vision.md), [`01-system-requirements.md`](01-system-requirements.md), [`02-feature-list.md`](02-feature-list.md) (all Approved v1.0.0) |
| Purpose | Definitive Role-Based Access Control (RBAC) specification for Nursilo |
| Next gated doc | `04-system-architecture.md` (documentation order revised; roadmap deferred) |

---

## 1. Purpose

Nursilo is a content-heavy **Nursing Learning Ecosystem** with a freemium Assessment System at its core. Many actors touch the same objects—questions, exams, books, subscriptions, and payments—with very different intents.

RBAC exists to:

- Protect learners from unauthorized admin/content surfaces
- Enforce editorial quality (Draft → Review → Approved → Published → Archived)
- Prevent entitlement bypass (free vs premium)
- Separate content creation from publication and from system security control
- Make privileged actions **auditable**
- Remain extensible for future Institution Administrator, Instructor, Moderator, and Support Agent roles **without redesigning V1 roles**

This document is the authoritative permission model for product, engineering, QA, and operations. It does **not** define database schemas, API endpoints, or application code.

---

## 2. Design Principles

| Principle | Meaning for Nursilo |
| --- | --- |
| **Least Privilege** | Each role receives only the minimum permissions required for its job. Prefer deny-by-default. |
| **Separation of Duties** | High-risk combinations are split: Authors draft; Reviewers approve; Editors/Admins publish; Super Admin alone owns security-critical configuration. |
| **Explicit Permissions** | Access is granted by named permissions, not by informal “staff” flags. Absence of a permission means deny. |
| **Auditable Actions** | Security- and content-critical actions produce durable audit records (see Section 10). |
| **Future Extensibility** | V1 roles remain stable. Future roles (Section 11) are additive placeholders and must not weaken V1 boundaries. |

### Supporting rules

1. **Server-side enforcement** — UI hiding is not authorization.
2. **Fail closed** — unknown role or missing permission → deny.
3. **Entitlements ≠ roles** — Free/Premium is a subscription entitlement on Student capabilities, not a separate RBAC role.
4. **Soft delete preference** — “Delete” for educational content means archive/soft-delete unless Super Admin explicitly performs a controlled hard-delete path (not a V1 student/author capability).
5. **Preview is privileged** — unpublished preview is never a Student capability.

---

## 3. Role Hierarchy

```text
Super Admin
    └── Admin
            ├── Editor
            │     └── Author
            ├── Reviewer
            └── (operational scopes under Admin)
Student  (isolated consumer role; not above/below content staff)
```

**Notes**

- Hierarchy expresses **authority and escalation**, not automatic inheritance of every permission (see Section 9).
- **Student** is intentionally isolated from the staff ladder.
- A user holds **one primary staff/student role** in V1 for clarity. Dual-hat accounts (e.g., Author who is also Student for testing) may exist operationally but permissions are the **union** of assigned roles; production content staff should not use personal learning accounts for privileged publish actions when avoidable.

### 3.1 Super Admin

**Responsibility:** Ultimate platform authority and security ownership.

- Owns system settings, feature toggles, payment configuration, backup operations, and role management
- May perform any Admin action when necessary
- Account should be tightly limited in number and protected with strongest operational controls

### 3.2 Admin

**Responsibility:** Day-to-day platform operations.

- User management (except Super Admin–only constraints)
- Subscription/payment operations (grant/revoke, triage), reports, announcements
- Broad content operations including publish/archive where policy allows
- Cannot change Super Admin–only security/payment/backup/role-definition settings

### 3.3 Editor

**Responsibility:** Content quality lead across learning, books, questions, and CMS.

- Edit and coordinate content across the hierarchy
- Publish Approved content; archive Published content
- Preview unpublished content
- Import/export content as permitted
- Does not own system security settings or role definitions

### 3.4 Reviewer

**Responsibility:** Pedagogical and factual gate before publication.

- Review submitted content and questions
- Approve or reject (return to Draft)
- Preview unpublished content
- Does not publish by default (separation of duties); may View reports related to content quality

### 3.5 Author

**Responsibility:** Create and revise Draft educational assets.

- Create/edit Draft learning materials, questions, and related drafts within scope
- Submit for Review
- Cannot approve, publish, manage users, or change subscriptions/payments

### 3.6 Student

**Responsibility:** Learn, practice, take exams, manage personal study data.

- Consume Published content per Free/Premium entitlements
- No access to admin, editorial, or unpublished content (except their own personal notes/bookmarks/attempts)

---

## 4. Permission Matrix

Legend:

| Symbol | Meaning |
| --- | --- |
| **Y** | Allowed |
| **—** | Denied |
| **L** | Limited / scoped (see notes under table or role sections) |
| **E** | Allowed only when Student entitlement (Free/Premium) permits |

Soft-delete/archive is the default destructive action for content. Hard delete is Super Admin–controlled and not shown as a normal staff “Delete” unless noted.

### 4.1 User Management

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View users | Y | Y | — | — | — | — |
| Create users | Y | Y | — | — | — | — |
| Edit users | Y | Y | — | — | — | L (self profile only) |
| Disable / suspend users | Y | Y | — | — | — | — |
| Delete users (controlled) | Y | L | — | — | — | — |
| View own profile | Y | Y | Y | Y | Y | Y |
| Edit academic profile | — | — | — | — | — | Y |

**Notes:** Students edit only their own basic + academic profile. Admin must not demote/remove the last Super Admin. Deleting Super Admin accounts is Super Admin–only.

### 4.2 Role Management

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View roles | Y | L | — | — | — | — |
| Assign roles | Y | L | — | — | — | — |
| Define / modify role permission sets | Y | — | — | — | — | — |
| Grant Super Admin | Y | — | — | — | — | — |

**Notes:** Admin may assign Author/Reviewer/Editor/Student (and Admin only if Super Admin policy allows; default **Admin cannot create Super Admin**). Role *definition* changes are Super Admin–only.

### 4.3 Learning Content

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View published | Y | Y | Y | Y | Y | E |
| View unpublished | Y | Y | Y | Y | L (own/assigned drafts) | — |
| Create | Y | Y | Y | — | Y (Draft) | — |
| Edit | Y | Y | Y | L (review annotations / return) | Y (Draft) | — |
| Approve | Y | Y | L | Y | — | — |
| Publish | Y | Y | Y | — | — | — |
| Archive / soft-delete | Y | Y | Y | — | — | — |
| Restore from archive | Y | Y | Y | — | — | — |
| Preview unpublished | Y | Y | Y | Y | L | — |
| Import | Y | Y | Y | — | — | — |
| Export | Y | Y | Y | — | L | — |
| Manage M2M relationships | Y | Y | Y | — | L (draft scope) | — |

### 4.4 Books

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View catalog (published) | Y | Y | Y | Y | Y | E |
| View unpublished | Y | Y | Y | Y | L | — |
| Create | Y | Y | Y | — | Y (Draft) | — |
| Edit | Y | Y | Y | L | Y (Draft) | — |
| Approve | Y | Y | L | Y | — | — |
| Publish | Y | Y | Y | — | — | — |
| Archive / soft-delete | Y | Y | Y | — | — | — |
| Restore | Y | Y | Y | — | — | — |
| Read online | Y | Y | Y | Y | Y | E |
| Download | Y | Y | Y | — | — | E |
| Import / Export | Y | Y | Y | — | — | — |

### 4.5 Question Bank

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View published questions | Y | Y | Y | Y | Y | E |
| View unpublished | Y | Y | Y | Y | L | — |
| Create | Y | Y | Y | — | Y | — |
| Edit | Y | Y | Y | L | Y (Draft / returned) | — |
| Approve | Y | Y | L | Y | — | — |
| Publish | Y | Y | Y | — | — | — |
| Archive / soft-delete | Y | Y | Y | — | — | — |
| Restore | Y | Y | Y | — | — | — |
| Import | Y | Y | Y | — | — | — |
| Export | Y | Y | Y | — | L | — |
| View error reports | Y | Y | Y | Y | L (own items) | — |
| Resolve error reports | Y | Y | Y | L | — | — |
| Duplicate detection tools | Y | Y | Y | — | Y | — |

Detailed assessment workflow permissions: **Section 6**.

### 4.6 Exams & Mock Tests

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View exam definitions | Y | Y | Y | L | L | E (available sets) |
| Create exam / mock definitions | Y | Y | Y | — | L | — |
| Edit exam / mock definitions | Y | Y | Y | — | L | — |
| Publish exam / mock sets | Y | Y | Y | — | — | — |
| Archive exam / mock sets | Y | Y | Y | — | — | — |
| Take practice / exams | — | — | — | — | — | E |
| Resume interrupted exam | — | — | — | — | — | E |
| View own attempts / history | — | — | — | — | — | Y |
| View any learner attempts | Y | Y | L | — | — | — |
| Configure premium tracks | Y | Y | L | — | — | — |

**Notes:** Staff taking exams for QA should use Student-capable test accounts. Production Admin “impersonation” is not a V1 requirement.

### 4.7 Editorial Workflow

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| Create Draft | Y | Y | Y | — | Y | — |
| Submit for Review | Y | Y | Y | — | Y | — |
| Approve | Y | Y | L | Y | — | — |
| Reject / return to Draft | Y | Y | Y | Y | — | — |
| Publish | Y | Y | Y | — | — | — |
| Archive | Y | Y | Y | — | — | — |
| Restore | Y | Y | Y | — | — | — |
| Preview unpublished | Y | Y | Y | Y | L | — |

Detailed editorial matrix: **Section 5**.

### 4.8 Blog & CMS

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View public pages/posts | Y | Y | Y | Y | Y | Y (public) |
| Create | Y | Y | Y | — | L | — |
| Edit | Y | Y | Y | L | L | — |
| Approve | Y | Y | L | Y | — | — |
| Publish | Y | Y | Y | — | — | — |
| Archive | Y | Y | Y | — | — | — |
| Manage SEO metadata | Y | Y | Y | — | — | — |
| Contact/feedback triage | Y | Y | L | — | — | Submit only |

### 4.9 Notifications & Announcements

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View own notifications | Y | Y | Y | Y | Y | Y |
| Create announcements | Y | Y | L | — | — | — |
| Publish / unpublish announcements | Y | Y | L | — | — | — |
| Send system notifications | Y | Y | — | — | — | — |

### 4.10 Reports & Analytics

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| Own learning analytics | — | — | — | — | — | E (advanced = Premium) |
| Admin usage overview | Y | Y | L | — | — | — |
| Content performance analytics | Y | Y | Y | L | — | — |
| Question usage statistics | Y | Y | Y | L | L (own) | — |
| Export operational reports | Y | Y | L | — | — | — |

### 4.11 Subscriptions & Payments

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| View own subscription | — | — | — | — | — | Y |
| Purchase / checkout | — | — | — | — | — | Y |
| View all subscriptions | Y | Y | — | — | — | — |
| Manual grant / revoke premium | Y | Y | — | — | — | — |
| View payment events | Y | Y | — | — | — | — |
| Configure payment gateways | Y | — | — | — | — | — |
| Refund / financial corrections | Y | L | — | — | — | — |

### 4.12 Website Settings, System Settings, Audit Logs

| Permission | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| Website settings (public content, branding copy) | Y | Y | L | — | — | — |
| System settings (security, env-critical) | Y | — | — | — | — | — |
| Feature toggles | Y | — | — | — | — | — |
| Freemium caps / plan configuration | Y | L | — | — | — | — |
| View audit logs | Y | Y | — | — | — | — |
| Export audit logs | Y | L | — | — | — | — |
| Backup operations | Y | — | — | — | — | — |
| Payment configuration | Y | — | — | — | — | — |

---

## 5. Editorial Permissions

Lifecycle:

```text
Draft → Review → Approved → Published → Archived
         ↑__________________|  (reject/return)
Archived → (Restore) → previous workable state (typically Draft or Approved per policy)
```

| Action | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| **Create Draft** | Y | Y | Y | — | Y | — |
| **Submit for Review** | Y | Y | Y | — | Y | — |
| **Approve** | Y | Y | L | Y | — | — |
| **Reject / return to Draft** | Y | Y | Y | Y | — | — |
| **Publish** | Y | Y | Y | — | — | — |
| **Archive** | Y | Y | Y | — | — | — |
| **Restore** | Y | Y | Y | — | — | — |
| **Preview unpublished** | Y | Y | Y | Y | L (own drafts) | — |

### Editorial rules

1. **Authors cannot Approve or Publish** — Separation of Duties.
2. **Reviewers cannot Publish** in V1 default policy — they Approve; Editors/Admins Publish.
3. **Editor Approve (L)** — Editors may Approve when acting as senior content leads; preferred happy path remains Reviewer Approve → Editor Publish.
4. **Students never see** Draft, Review, Approved (unpublished), or Archived items in learner discovery.
5. All transitions in this table are **audit-logged**.

---

## 6. Assessment Permissions

Applies to Question Bank items and related assessment configuration.

| Action | Super Admin | Admin | Editor | Reviewer | Author | Student |
| --- | --- | --- | --- | --- | --- | --- |
| **Create Questions** | Y | Y | Y | — | Y | — |
| **Edit Questions** | Y | Y | Y | L | Y (non-published or returned Draft) | — |
| **Approve Questions** | Y | Y | L | Y | — | — |
| **Publish Questions** | Y | Y | Y | — | — | — |
| **Archive Questions** | Y | Y | Y | — | — | — |
| **Restore Questions** | Y | Y | Y | — | — | — |
| **Import Questions** | Y | Y | Y | — | — | — |
| **Export Questions** | Y | Y | Y | — | L | — |
| **View Question Reports** (error reports) | Y | Y | Y | Y | L | — |
| **Resolve Question Reports** | Y | Y | Y | L | — | — |
| **View Question Usage Statistics** | Y | Y | Y | L | L | — |
| **Use Duplicate Detection** | Y | Y | Y | — | Y | — |

### Assessment integrity rules

1. Editing a **Published** question must preserve historical attempts via versioning/equivalent strategy; permission to edit does not grant permission to rewrite history.
2. Students may **attempt**, **bookmark**, and **report errors** on entitled published questions only.
3. Students may **not** create, edit, approve, publish, import, or export question bank items.
4. Import/Export are staff-only and audit-logged.

---

## 7. Student Permissions

### 7.1 Students may

| Area | Allowed actions |
| --- | --- |
| Account | Register, login, logout, password reset, edit basic profile, maintain academic profile, set UI language |
| Learning | Browse/open **Published** learning content per entitlement; Continue Learning; track personal progress |
| Assessment | Practice (topic/chapter/subject/random/custom) within Free caps or Premium rights; take exams/mocks; resume interrupted exams; review wrong answers and bookmarks; view own exam history |
| Library | Read entitled books online; download only when entitlement/policy allows; bookmark (when feature available) |
| Dashboard | Today’s Goal, streak, weak/strong topics (per entitlement), notes, bookmarks, recent activity, subscription status, notifications |
| Search | Global search with entitlement-aware results |
| Public CMS | Read public blog/pages; submit contact/feedback |
| Subscription | View status; purchase Premium when payments enabled |
| Personal data | CRUD own notes; manage own bookmarks |

### 7.2 Students may not

| Forbidden |
| --- |
| Access any admin or staff console |
| View or preview unpublished content |
| Create/edit/approve/publish/archive learning objects, books, or questions |
| Import/export catalog content |
| Assign roles or manage users |
| View other learners’ attempts, notes, or private data |
| Configure payments, system settings, feature toggles, or backups |
| Bypass Free/Premium entitlements |
| Permanently delete exam history (V1) |
| Issue or manage certificates (non-feature) |
| Act as Institution Administrator (Future only) |

### 7.3 Entitlement overlay (not roles)

| Capability | Free Student | Premium Student |
| --- | --- | --- |
| Core learning materials | Y | Y |
| Limited practice | Y (capped) | Y |
| Complete question bank | — | Y |
| Unlimited mocks | — | Y |
| Licensing / Govt / NCLEX / Prometric tracks | Teaser only / — | Y |
| Premium books & notes | — | Y |
| Advanced analytics | — | Y |

---

## 8. Administrative Boundaries (Super Admin only)

The following are **Super Admin exclusive** in Version 1:

| Area | Super Admin–only actions |
| --- | --- |
| **System Settings** | Security-critical configuration, environment-sensitive settings, global kill switches |
| **Role Management** | Define/modify role permission sets; grant/revoke Super Admin |
| **Critical Security Settings** | Auth security policy knobs, forced credential resets at platform level, security feature flags |
| **Payment Configuration** | Gateway credentials, webhook secrets, merchant configuration |
| **Backup Operations** | Initiate/manage backup and restore operations (as productized) |
| **Feature Toggles** | Enable/disable major platform modules/features globally |

### Admin may (related but bounded)

- Manage users and assign non–Super Admin roles (per policy)
- Manual premium grant/revoke (audit-logged)
- View payment events and subscriptions
- Manage day-to-day website content settings (non-security)
- View audit logs
- Configure freemium numeric caps only if Super Admin delegates via settings policy (**default:** Super Admin sets plan model; Admin may adjust operational caps if explicitly enabled)

If unclear whether an action is security-critical, classify it as **Super Admin only**.

---

## 9. Permission Inheritance

### 9.1 Inherited (authority cascade)

| From | Inherits practical ability to |
| --- | --- |
| Super Admin | Perform all Admin, Editor, Reviewer, and Author content/operations actions when required |
| Admin | Perform Editor-level content operations and operational user/subscription actions (except Super Admin–only boundaries) |
| Editor | Perform Author-level drafting plus publish/archive/import/export (as matrixed) |

### 9.2 Intentionally isolated (do not inherit casually)

| Isolation | Rule |
| --- | --- |
| **Student ↔ Staff** | Student permissions never grant staff permissions; staff hierarchy never implies learner entitlement bypass for personal study accounts without explicit Student entitlement |
| **Reviewer Publish** | Reviewer does **not** inherit Publish |
| **Author Approve/Publish** | Author does **not** inherit Approve or Publish |
| **Payment config** | Not inherited by Admin |
| **Role definition** | Not inherited by Admin |
| **Backup / feature toggles** | Not inherited by Admin |
| **Other learners’ private data** | Not inherited by Editor/Author/Reviewer |

### 9.3 Effective permission resolution

1. Deny by default  
2. Union permissions of all assigned roles  
3. Apply Super Admin–only denials to non–Super Admins  
4. Apply entitlement checks for Student consumption  
5. Audit privileged outcomes  

---

## 10. Audit Requirements

The following action classes **must always** produce audit log entries (actor, timestamp, action, target type/id, summary metadata):

| Category | Must-log actions |
| --- | --- |
| **Authentication** | Login success/failure (policy-appropriate), logout (optional), password reset completion |
| **Roles** | Role assignment/change; Super Admin grant/revoke |
| **Editorial** | Submit for Review, Approve, Reject, Publish, Archive, Restore |
| **Questions** | Create, Edit (especially published edits/new versions), Approve, Publish, Archive, Import, Export |
| **Subscriptions** | Manual grant/revoke; plan changes |
| **Payments** | Payment initiated, payment confirmed, payment failed, webhook processed, refund/correction |
| **Announcements** | Create, publish, unpublish |
| **Settings** | System settings changes; feature toggles; payment configuration changes |
| **Security** | Backup/restore operations; critical security setting changes |
| **User admin** | User create/disable/delete; privilege escalations |

### Audit access

| Role | Audit access |
| --- | --- |
| Super Admin | Full view/export |
| Admin | View (export limited) |
| Editor / Reviewer / Author / Student | No general audit log access |

Audit logs themselves must not be editable by Admin.

---

## 11. Future Roles (placeholders only)

These roles are **out of scope for Version 1**. They must not be implemented in V1 permission checks and must not weaken current boundaries.

| Future role | Intended purpose (non-binding) |
| --- | --- |
| **Institution Administrator** | Manage institutional seats, cohorts, and org-level reporting after product-market fit |
| **Instructor** | Guide assigned learner groups; limited progress visibility; no system settings |
| **Moderator** | Moderate question discussions / community content (pairs with future Question Discussion) |
| **Support Agent** | Handle contact/feedback, view limited subscription status, assist password/support flows without content publish rights |

### Future-role rules

1. Additive only — introduce via explicit backlog + RBAC revision  
2. Default deny until granted  
3. Institution Administrator must not equal Super Admin  
4. Support Agent must not configure payments or roles  
5. Moderator must not publish question bank items by default  

---

## 12. Mapping to Product Backlog (traceability)

| RBAC concern | Example backlog features |
| --- | --- |
| Roles & least privilege | FEAT-AUTH-06, FEAT-ADM-02 |
| Editorial workflow | FEAT-EDT-01…05 |
| Assessment permissions | FEAT-QB-*, FEAT-ADM-04 |
| Student entitlements | FEAT-SUB-01…03, FEAT-PRC-04, FEAT-EXM-06 |
| Audit logging | FEAT-ADM-03 |
| Announcements / contact | FEAT-NTF-03, FEAT-CMS-04 |
| Future roles | FEAT-FUT-10, FEAT-FUT-13 |

---

## 13. Acceptance Criteria (Document Level)

This RBAC specification is acceptable when:

1. All six V1 roles have clear responsibilities and matrix coverage.  
2. Editorial and assessment permission tables unambiguously separate Draft / Review / Approve / Publish.  
3. Super Admin–only boundaries are explicit.  
4. Student allow/deny lists and entitlement overlay are complete for V1.  
5. Inheritance vs isolation rules prevent accidental privilege creep.  
6. Audit must-log categories match `01` / `02` requirements.  
7. Future roles are reserved without affecting V1.

---

## 14. Document Lock

**Status:** `docs/03-user-roles.md` is **Approved** and locked at **Version 1.0.0**.

This document is the definitive RBAC specification for Nursilo. Documentation order is revised: next gated document is `docs/04-system-architecture.md` (development roadmap deferred). Proceed only when explicitly requested.

---

*Nursilo — Learn. Practice. Succeed.*
