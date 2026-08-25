# Nursilo — Project Vision


| Field        | Value                                                                |
| ------------ | -------------------------------------------------------------------- |
| Document     | `00-project-vision.md`                                               |
| Version      | `1.0.0`                                                              |
| Status       | **Approved** — locked foundation document                            |
| Product      | Nursilo                                                              |
| Domain       | [https://nursilo.ahmad.bd](https://nursilo.ahmad.bd)                 |
| Audience     | Founders, product owners, architects, engineers, future stakeholders |
| Related docs | `01`–`15` (gated; start only when requested after this lock)         |


---

## 1. Executive Summary

**Nursilo** is a Bangladesh-first **Nursing Learning Ecosystem** built to help nursing students and practicing nurses learn deeply, practice deliberately, and succeed in academic, licensing, government job, and international exams.

Nursilo is **not** a generic Learning Management System (LMS). Course content exists to support exam preparation. The **Assessment System** (Question Bank + Practice + Exam + Review + Analytics) is the product's core domain. Learning materials, practice sessions, mock tests, and performance analytics form one connected content-driven system.

Version 1 is a **freemium B2C** web platform for individual learners. Users can register and access core learning materials and limited practice for free. Premium subscriptions unlock the full question bank, unlimited mocks, specialized exam preparation tracks, premium books and notes, and advanced analytics.

There is **no certificate module**. Students come to Nursilo to learn and pass exams—not to collect certificates.

The architecture is **AI-ready**: Version 1 does not ship AI features, but domain services, content structure, and analytics signals are designed so future AI tutor and adaptive learning capabilities can plug in without rewriting the core platform.

---



## 2. Brand Identity


| Element           | Statement                                                                                                                                                                                          |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Brand name**    | Nursilo                                                                                                                                                                                            |
| **Domain**        | [https://nursilo.ahmad.bd](https://nursilo.ahmad.bd)                                                                                                                                               |
| **Tagline**       | Learn. Practice. Succeed.                                                                                                                                                                          |
| **Mission**       | To become the most trusted digital nursing learning platform in Bangladesh by providing high-quality learning resources, smart practice, and exam preparation for every stage of a nurse's career. |
| **Vision**        | Empower every nursing student and nurse with accessible, technology-driven education that improves knowledge, clinical confidence, and exam success.                                               |
| **Strategic aim** | Nursilo aims to become the single source of truth for nursing education, practice, and examination preparation in Bangladesh.                                                                      |


---



## 3. Problem Statement

Nursing education and exam preparation in Bangladesh are fragmented:

- Study materials are scattered across books, notes, coaching centers, and informal social channels.
- Practice systems rarely mirror real exam conditions or provide meaningful review of wrong answers.
- Bangla and English learners often lack a single bilingual platform designed for both languages from day one.
- Learners preparing for BNMC-oriented licensing, government jobs, NCLEX, and Prometric must switch between unrelated tools.
- Progress is hard to measure: weak topics stay weak, strong topics are over-practiced, and study habits lack continuity.
- Institutional LMS tools emphasize enrollment and certificates more than high-volume question practice and exam analytics.

Nursilo addresses these gaps with one coherent ecosystem centered on practice, exams, and measurable improvement.

---



## 4. Solution Overview

Nursilo unifies learning content, a rich question bank, a flexible exam engine, a multi-format book library, learner analytics, and freemium subscriptions into a single production-ready platform.

### 4.1 What learners get

- Structured nursing courses and subject-wise learning
- Lesson notes and learning materials tied to the curriculum hierarchy
- Multi-format book library (PDF, EPUB, HTML articles, image-based resources) with premium access controls
- Topic, chapter, subject, random, custom, timed, and mock exam practice
- Licensing, government job, NCLEX, and Prometric preparation tracks (premium)
- Bookmarks, personal notes, global search, notifications, and a student dashboard
- Performance analytics that surface weak and strong topics over time



### 4.2 What the business delivers

- A trusted Bangladesh-first brand for nursing exam success
- A freemium funnel from free core value to paid depth
- An API-ready backend that can later power Flutter mobile apps without rewriting business logic
- An AI-ready modular architecture that can grow into AI tutor, clinical case simulation, and adaptive learning **after** Version 1

---



## 5. Target Users



### 5.1 Primary (Version 1)

Version 1 optimizes exclusively for **individual learners**:

- Diploma in Nursing Science & Midwifery students
- BSc in Nursing students
- Diploma in Midwifery students
- Post Basic BSc Nursing students
- MSc Nursing students
- Internship nurses
- Registered nurses



### 5.2 Secondary (same product, specialized prep tracks)

- Government job candidates
- NCLEX candidates
- Prometric candidates



### 5.3 Deferred (post product-market fit)

Institutional plans for nursing colleges, hospitals, and coaching centers are **intentionally postponed** until Nursilo reaches product-market fit with individual learners.

---



## 6. High-Level Administrative Roles

Detailed permissions belong in `03-user-roles.md`. At vision level, Nursilo recognizes these roles:


| Role            | Intent                                                                                                     |
| --------------- | ---------------------------------------------------------------------------------------------------------- |
| **Super Admin** | Full platform control: settings, roles, billing configuration, and system-wide oversight                   |
| **Admin**       | Operational administration of users, content operations, subscriptions, and day-to-day platform management |
| **Editor**      | Edits and coordinates content across the learning hierarchy, books, and question bank                      |
| **Reviewer**    | Reviews submitted content for accuracy, pedagogy, and publication readiness                                |
| **Author**      | Creates draft learning materials, questions, and related educational assets                                |
| **Student**     | Learns, practices, takes exams, and consumes freemium or premium entitlements                              |


---



## 7. Content Sources

Educational content on Nursilo originates from controlled, attributable sources—not anonymous scrapes. Primary sources include:

- **Original Nursilo content** — Curriculum-aligned lessons, notes, explanations, and practice items created by the Nursilo content team
- **Subject-matter experts** — Nursing educators, clinicians, and exam-prep specialists contributing under editorial review
- **Licensed or permitted references** — Books, editions, and reference materials used with appropriate rights and clear attribution
- **Curated public educational assets** — Diagrams and reference materials incorporated only when licensing and clinical accuracy allow
- **Internal adaptations** — Reusable learning objects remixed and composed across courses/topics without duplicating source-of-truth content

All published content must pass the editorial workflow (Section 8) before learners see it.

---



## 8. Editorial Workflow

Content quality is enforced through a standard lifecycle:

```text
Draft → Review → Approved → Published → Archived
```


| Stage         | Meaning                                                       |
| ------------- | ------------------------------------------------------------- |
| **Draft**     | Authoring in progress; not visible to learners                |
| **Review**    | Submitted for pedagogical and factual review                  |
| **Approved**  | Accepted for publication; may await scheduling                |
| **Published** | Live for entitled learners (free or premium per access rules) |
| **Archived**  | Removed from active discovery; retained for history and audit |


Workflow details, permissions, and audit trails are specified in later admin and security documents.

---



## 9. Product Principles

1. **Ecosystem, not LMS** — Nursilo is a Nursing Learning Ecosystem. Certificates are out of scope; exam success is the outcome.
2. **Practice first** — The **Assessment System** (Question Bank + Practice + Exam + Review + Analytics) is the core domain. Courses and lessons exist to support better practice and exam performance. Future architecture documents must treat this Assessment System as the product's core domain.
3. **Content-driven connectivity** — Every learning object should eventually connect through a single hierarchy (see Section 10).
4. **Reusable and composable content** — Educational objects are designed once and composed across courses, topics, practice sets, and exams—not copied into siloed duplicates.
5. **Freemium honesty** — Free users receive real learning value; premium unlocks depth, volume, specialization, and advanced insight—not a hollow trial.
6. **Bangladesh first** — Curriculum relevance, Bangla + English support, and local payment readiness (bKash, Nagad, SSLCommerz in future payment phases).
7. **API-first design** — Version 1 ships with Django Templates, but business logic stays reusable for future Flutter clients.
8. **AI-ready architecture** — Structure content, attempts, and analytics so future AI tutor and adaptive learning features can integrate cleanly.
9. **Phase discipline** — Build one phase, approve, then continue. No big-bang delivery.
10. **Production from day one** — Security, performance, observability, and maintainability are design constraints—not afterthoughts.

---



## 10. Freemium Business Model



### 10.1 Free tier

Registered users can access:

- Core learning materials
- Limited practice



### 10.2 Premium subscriptions unlock

- Complete question bank
- Unlimited mock exams
- Licensing exam preparation
- Government job preparation
- NCLEX preparation
- Prometric preparation
- Premium books and notes
- Advanced analytics
- Future offline / PWA features (post–Version 1)



### 10.3 Payments (future implementation detail)

When payment integration is built, Bangladesh-first gateways take priority:

- bKash
- Nagad
- SSLCommerz

International payment providers may follow later. Detailed payment architecture belongs in later documents (`02`, `10`, `11`, `14`).

### 10.4 Institutional revenue

Institutional licensing (colleges, hospitals, coaching centers) is a **later** business expansion after individual freemium product-market fit.

---



## 11. Content-Driven Learning Hierarchy

Nursilo’s content model is hierarchical and relational. Learning objects are not isolated pages; they form a connected graph that powers practice, exams, and analytics:

```text
Course
  → Subject
    → Unit
      → Chapter
        → Topic
          → Lesson
            → Learning Material
              → Question Bank
                → Practice
                  → Exam
                    → Analytics
```

This hierarchy is a product vision constraint: later database design, admin workflows, and APIs must preserve these relationships so progress, bookmarks, weak-topic detection, and exam generation remain consistent. Content must remain **reusable and composable** across this graph rather than duplicated per course or exam.

---



## 12. Core Capability Pillars


| Pillar                             | Role in the ecosystem                                                                                                                                                                                                 |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Learning**                       | Courses, subjects, units, chapters, topics, lessons, and learning materials                                                                                                                                           |
| **Question Bank**                  | MCQ, True/False, Best Answer, Clinical Scenario Questions, and Image-Based questions with explanations, references, difficulty (**Easy, Medium, Hard, Expert**), tags, bookmarks, and error reporting                 |
| **Exam Engine**                    | Topic / chapter / subject / random / custom / timed practice, mock tests, wrong-answer review, progress tracking                                                                                                      |
| **Book Library**                   | Multi-format library supporting **PDF**, **EPUB**, **HTML articles**, and **image-based resources**, with category, subject, author, edition, publisher, cover, online reading, premium access, bookmarks, and search |
| **Student Dashboard**              | Continue learning, goals, streak, exam history, weak/strong topics, bookmarks, notes, notifications, subscription status, analytics                                                                                   |
| **Admin & CMS**                    | Users, roles, content hierarchy, editorial workflow, questions, exams, books, blog, pages, notifications, subscriptions, payments, settings, analytics, logs                                                          |
| **Subscriptions & Access Control** | Freemium entitlements enforced consistently across web (and later API/mobile)                                                                                                                                         |
| **Global Search & Engagement**     | Global search across **courses, books, lessons, questions, and authors**; plus blog, notifications, and personal notes                                                                                                |




### 12.1 Question difficulty standard

Every scored practice/exam question uses one of these difficulty levels:


| Level      | Intent                                                    |
| ---------- | --------------------------------------------------------- |
| **Easy**   | Foundational recall and basic application                 |
| **Medium** | Standard curriculum and common exam items                 |
| **Hard**   | Multi-step reasoning or less common presentations         |
| **Expert** | Advanced clinical judgment and high-stakes exam readiness |




### 12.2 Question types (terminology)

Supported question types include:

- MCQ
- True / False
- Best Answer
- **Clinical Scenario Questions**
- Image-Based Questions

---



## 13. Explicit Non-Goals (Version 1)

The following are **out of scope** for Version 1:

- Course certificates or certificate modules of any kind
- Institutional billing, seat management, or college admin portals
- AI tutor and AI-assisted learning product features (architecture remains AI-ready)
- Clinical case simulation as a dedicated product mode
- Adaptive learning engines as a shipped product feature
- Flutter Android / iOS apps (API-first prepares for them)
- Progressive Web App / offline-first features
- Centralized media/image library as a full product surface (see Section 14 foreshadowing)
- OSCE preparation, nursing procedures modules, flashcards, and medical calculators as Version 1 features
- Redis, Celery, Cloudflare R2, and other scale-out infrastructure until justified by load and product need
- International payment providers as the primary checkout path

These items belong on the future roadmap and must not dilute Version 1 scope.

---



## 14. Future Roadmap Notes (Vision Level)

Detailed planning belongs in `15-future-roadmap.md`. At vision level, Nursilo anticipates:


| Theme              | Direction                                                                                                              |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| **AI**             | AI tutor, AI-assisted explanations, and adaptive learning built on AI-ready architecture                               |
| **Clinical depth** | Clinical case simulation; richer Clinical Scenario Question experiences                                                |
| **Skills & OSCE**  | OSCE preparation and nursing procedures learning                                                                       |
| **Study tools**    | Flashcards and medical calculators                                                                                     |
| **Media library**  | Centralized media/image library for anatomy diagrams and medical assets, reusable across lessons, questions, and books |
| **Clients**        | Flutter Android/iOS and PWA / offline features                                                                         |
| **Institutions**   | College, hospital, and coaching-center plans after product-market fit                                                  |
| **Infrastructure** | Redis, Celery, Cloudflare R2, and related scale-out components when warranted                                          |


---



## 15. Architecture Principles

All Nursilo documentation and implementation must follow these principles:


| Principle                                  | Meaning for Nursilo                                                                                                              |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| **Simplicity over unnecessary complexity** | Prefer clear Django apps and straightforward flows over premature abstraction                                                    |
| **Modular architecture**                   | Loosely coupled apps; clear boundaries between domains                                                                           |
| **Scalable database design**               | PostgreSQL schemas that grow with content volume and analytics without table duplication for languages                           |
| **Production-ready from the beginning**    | Environments, secrets, backups, logging, and secure defaults planned early                                                       |
| **Clean Architecture where practical**     | Separate presentation, application/services, and data access; keep business rules out of templates and views where reuse matters |
| **SOLID where appropriate**                | Especially for exam generation, entitlement checks, and analytics services                                                       |
| **Django best practices**                  | Explicit apps, settings split, migrations discipline, ORM-first, tested critical paths                                           |
| **Security by design**                     | AuthN/AuthZ, CSRF, XSS, injection, entitlement bypass, and payment integrity considered in design                                |
| **Performance by design**                  | Query discipline, caching strategy when needed, efficient exam attempt storage                                                   |
| **Accessibility & responsive design**      | Mobile-friendly UI usable by students on common devices                                                                          |
| **SEO-friendly public pages**              | Marketing, blog, and public content pages optimized for discovery                                                                |
| **API-first**                              | Version 1 UI is Django Templates + HTMX + Alpine.js; domain logic remains reusable for DRF and future Flutter clients            |
| **AI-ready**                               | Content graph, attempt data, and analytics designed for future AI tutor and adaptive learning without core rewrites              |
| **Reusable and composable content**        | Prefer shared learning objects linked into multiple contexts over duplicated copies                                              |
| **Multilingual from day one**              | Bangla and English supported without duplicating database tables; implementation details deferred to later architecture docs     |


---



## 16. Technology Direction (High Level)

Version 1 direction (detailed in later architecture and deployment docs):


| Layer      | Choice                                                                |
| ---------- | --------------------------------------------------------------------- |
| Backend    | Python 3.13, Django 5, Django REST Framework, PostgreSQL              |
| Frontend   | Django Templates, Tailwind CSS, HTMX, Alpine.js, JavaScript, Chart.js |
| Deployment | cPanel Passenger, Cloudflare, PostgreSQL                              |
| Future     | Flutter (Android/iOS), PWA, Cloudflare R2, Redis, Celery              |


This document does not prescribe app layouts, schemas, or endpoints. Those belong in documents `05`–`14`.

---



## 17. Success Criteria



### 17.1 Qualitative

- Learners trust Nursilo as their primary nursing practice and exam-prep destination in Bangladesh.
- Free users experience enough value to return; premium users feel the upgrade is justified by depth and outcomes.
- Authors, reviewers, editors, and admins can manage the full hierarchy and question bank through a reliable editorial workflow.
- The platform remains maintainable and AI-ready as features expand.



### 17.2 Directional metrics (to be refined in requirements)

- Monthly active learners
- Free → premium conversion rate
- Practice and mock-exam volume per active user
- Retention (e.g., Day 7 / Day 30)
- Coverage and quality of question bank by subject/topic and difficulty
- Reduction in repeated mistakes on weak topics (analytics usefulness)

Exact targets will be defined with product ownership; this vision establishes the measurement themes only.

---



## 18. Documentation Sequence

This vision is **gate #1**. After approval, documentation continues one file at a time:


| #   | Document             | Purpose                                                               |
| --- | -------------------- | --------------------------------------------------------------------- |
| 01  | System requirements  | Functional and non-functional requirements                            |
| 02  | Feature list         | Prioritized feature inventory                                         |
| 03  | User roles           | Personas, permissions, entitlements                                   |
| 04  | Development roadmap  | Phased delivery plan                                                  |
| 05  | System architecture  | Runtime and component architecture                                    |
| 06  | Database design      | Schema, multilingual model, relationships                             |
| 07  | Django app structure | App boundaries and responsibilities                                   |
| 08  | UI pages             | Student and public page inventory                                     |
| 09  | Admin panel          | Admin UX and management surfaces                                      |
| 10  | API design           | DRF contracts for web and future mobile                               |
| 11  | Security             | Threat model and controls                                             |
| 12  | Folder structure     | Repository layout                                                     |
| 13  | Coding standards     | Engineering conventions                                               |
| 14  | Deployment plan      | cPanel, Cloudflare, operations                                        |
| 15  | Future roadmap       | AI, adaptive learning, OSCE, media library, mobile, PWA, institutions |


No application code will be generated until the architecture documentation set is approved.

---



## 19. Glossary


| Term                  | Definition                                                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Course**            | Top-level learning program aligned to a nursing pathway or exam track (for example, Diploma Nursing or NCLEX prep).                    |
| **Subject**           | Major academic or clinical area within a course (for example, Anatomy & Physiology).                                                   |
| **Unit**              | Ordered grouping of related chapters within a subject.                                                                                 |
| **Chapter**           | Curriculum block within a unit covering a coherent set of topics.                                                                      |
| **Topic**             | Focused area of study within a chapter; primary anchor for practice targeting and analytics.                                           |
| **Lesson**            | Teachable session under a topic, delivering explanation and guided learning.                                                           |
| **Learning Material** | Reusable content asset attached to a lesson or topic (notes, media, readings, or similar).                                             |
| **Practice**          | Low-stakes or formative question activity drawn from the Question Bank (by topic, chapter, subject, random, or custom).                |
| **Exam**              | Structured assessed attempt (timed, mock, chapter, subject, or custom) with scoring and review.                                        |
| **Assessment System** | Core product domain comprising Question Bank + Practice + Exam + Review + Analytics.                                                   |


---



## 20. Document Lock

**Status:** `docs/00-project-vision.md` is **Approved** and locked at **Version 1.0.0**.

This document is the accepted foundation for Nursilo. Proceed to `docs/01-system-requirements.md` **only when requested**. No code and no additional documentation will be produced until then.

---

*Nursilo — Learn. Practice. Succeed.*
