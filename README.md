# Campus Placement & Internship Portal

A robust, multi-page web application built with **Python 3.11+** and **Django 5.x** providing three role-based portals (**Student**, **Recruiter**, and **Placement Admin**). The system facilitates transparent campus hiring with server-enforced eligibility gating, strict recruitment stage transitions, real-time status synchronization, and append-only administrative audit logs.

---

## Table of Contents
- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Features per Role](#features-per-role)
- [Business Rules](#business-rules)
  - [Eligibility Gating](#eligibility-gating)
  - [Status Pipeline & Allowed Transitions](#status-pipeline--allowed-transitions)
  - [Company & Opportunity Moderation](#company--opportunity-moderation)
- [Credentials Table](#credentials-table)
- [Local Setup & Quickstart](#local-setup--quickstart)
- [Running Tests](#running-tests)
- [Folder Structure](#folder-structure)



---

## Project Overview

The **Campus Placement & Internship Portal** manages the end-to-end lifecycle of university recruitment:
1. **Employer Onboarding**: Recruiters register their organization and submit credentials for administrative compliance verification.
2. **Drive Publishing**: Once verified, recruiters publish job and internship openings with specific eligibility criteria (CGPA threshold, allowed branches, graduation year batch, and application deadline).
3. **Automated Eligibility Gating**: When students browse or attempt to apply, the server strictly checks academic criteria. Ineligible candidates receive clear, human-readable explanations and are blocked from submitting applications.
4. **Application Pipeline**: Candidates progress through a defined recruitment pipeline (`APPLIED` &rarr; `UNDER_REVIEW` &rarr; `SHORTLISTED` &rarr; `INTERVIEW` &rarr; `OFFERED`, or `REJECTED`). Students can withdraw from non-final stages.
5. **Real-Time Status Synchronization**: Students receive live updates every 15 seconds without full page refreshes via an asynchronous status feed endpoint.
6. **Institutional Oversight**: Placement Administrators review companies and postings, approve or reject them with mandatory documented reasons, and review append-only immutable audit logs.

---

## Tech Stack

- **Backend**: Python 3.11+, Django 5.x (`Django==5.2.18`)
- **Database**: SQLite
- **Architecture**: Server-rendered Django templates (No React, no separate REST framework)
- **Authentication & Security**: Custom User model (`accounts.User` extending `AbstractUser` with `role`), role-based decorators (`@student_required`, `@recruiter_required`, `@admin_required`), CSRF protection on all forms, object-level access controls
- **Frontend & Styling**: Bootstrap 5.3 & Bootstrap Icons via CDN, plus custom indigo-themed stylesheet (`static/css/custom.css`)
- **Real-Time Layer**: Vanilla JavaScript polling (`fetch`) with dynamic DOM badge and timeline updates (`static/js/status_feed.js`)

---

## Features per Role

### 1. Student Portal
- **Dashboard**: High-level statistics (total applications, shortlisted stages, interviews, job offers received), recent applications table, profile completion bar, and recommended open postings.
- **Profile Management**: View and edit academic profile (full name, branch, CGPA on 0.00–10.00 scale, graduation year, cloud resume link, phone number) with a real-time completion percentage indicator.
- **Browse Opportunities**: Search open postings by keyword; filter by opportunity type (Full-time Job / Internship), academic branch, and maximum required CGPA; sort by date or deadline; paginated at 9 cards per page. Shows proactive `"Eligible for you"` badge.
- **Proactive Eligibility Evaluation**: Detailed posting page highlights whether the student qualifies. If not eligible, clear bulleted reasons are displayed, and the Apply button is disabled.
- **Apply Confirmation**: Review academic snapshot before submission. Server validates eligibility on the POST request before recording the application.
- **My Applications**: Filterable list of all submitted applications with color-coded status badges, last update timestamps, and a live sync indicator (`"Updated just now"`).
- **Application Detail & Visual Timeline**: Interactive stepper/timeline visualizing every stage change from `ApplicationStatusHistory`. Includes candidate withdraw action with modal confirmation.

### 2. Recruiter Portal
- **Dashboard**: Overview cards for total postings, pending admin reviews, total applicants, and shortlisted candidates. Status banner displaying company verification state.
- **Company Profile**: Register and update company profile (legal name, website, industry, location, overview). Displays verification status (`PENDING`, `APPROVED`, `REJECTED`). If rejected, shows the admin's rejection reason; editing and saving resubmits for re-review.
- **Postings Management**: Table of all company drives with applicant counts, open/closed state, and administrative status badges. Includes quick toggle button to close or reopen applications.
- **Create & Edit Postings**: Create postings with branch multi-select, minimum CGPA, target graduation year, deadline, and package. Editing an approved posting resets its status to `PENDING` to ensure compliance.
- **Applicant Screening & Batch Transitions**: Table of applicants per posting with status filtering and CGPA sorting (highest first). Select multiple candidates using checkboxes to apply batch status transitions; invalid transitions are skipped and reported.
- **Applicant Detail**: Full student academic credentials, direct resume PDF link, single-candidate pipeline transition dropdown (restricted to permitted transitions), and private recruiter notes.

### 3. Placement Admin Portal (`/placement-admin/`)
- **Executive Dashboard**: Counts of pending companies, pending job postings, approved partners, total platform applications, and quick queue snippets.
- **Company Moderation Queue**: Review incoming recruiters and company registrations. Approve with one click, or reject with a mandatory documented reason.
- **Job Postings Queue & Inspection**: Review detailed job descriptions, compensation, and eligibility criteria before making roles visible to students.
- **Append-Only Audit Trail**: Dedicated audit logs page filterable by action (`APPROVED`, `REJECTED`) and target entity (`Company`, `JobPosting`). Displays snapshot admin ID, admin username, target label, recorded reason, and timestamp. Registered read-only in Django admin.
- **User Directory**: Searchable, role-filtered directory of all registered students, recruiters, and placement admins.

---

## Business Rules

### Eligibility Gating
All eligibility checks are centralized in `core.eligibility.check_eligibility(profile, posting)` and enforced on the server during application submission:
1. **Profile Completeness**: Candidate must have completed required profile fields (full name, branch, CGPA, graduation year, resume link).
2. **CGPA Threshold**: `profile.cgpa >= posting.min_cgpa`. Example failure message: `"You are not eligible: your CGPA is 6.80 but this role requires a minimum of 7.50."`
3. **Branch Qualification**: If `posting.allowed_branches` is specified, `profile.branch` must be in the allowed branches list. If empty, all engineering branches qualify.
4. **Graduation Batch Match**: If `posting.graduation_year` is set, `profile.graduation_year` must match.
5. **Deadline Validity**: `posting.deadline >= today`.
6. **Posting & Company Status**: Both `posting.status == 'APPROVED'` and `posting.company.status == 'APPROVED'`, and `posting.is_open == True`.
7. **Duplicate Prevention**: Student cannot apply more than once to the same posting (`unique_together = ('student', 'posting')`).

### Status Pipeline & Allowed Transitions
The hiring pipeline enforces valid transitions:
- **Pipeline Order**: `APPLIED` &rarr; `UNDER_REVIEW` &rarr; `SHORTLISTED` &rarr; `INTERVIEW` &rarr; `OFFERED`.
- **Rejections**: `REJECTED` is permitted from any non-final active state.
- **Final States**: `OFFERED`, `REJECTED`, and `WITHDRAWN` are final; no further transitions are allowed out of these states.
- **Withdrawals**: Students may withdraw an application at any point while it is in a non-final state (`APPLIED`, `UNDER_REVIEW`, `SHORTLISTED`, `INTERVIEW`).
- **Batch Resiliency**: During batch updates on the applicants list, candidates with invalid transitions (such as those already in a final state) are skipped and reported (`"X updated, Y skipped: invalid transition"`).
- **Audit Logging**: Every status transition generates an `ApplicationStatusHistory` record.

### Company & Opportunity Moderation
- **Posting Restriction**: Recruiters can only create job postings after their company profile has been approved by the placement admin.
- **Reset on Edit**: Modifying an approved job posting automatically resets its status back to `PENDING` for administrative re-review.
- **Rejection Resubmission**: Rejected companies or postings can be edited and resubmitted, resetting status to `PENDING` and clearing previous rejection reasons.
- **Mandatory Rejection Reasons**: Admins cannot reject a company or job posting without submitting a non-empty explanation, which is immutably recorded in `AdminActionLog`.

---

## Credentials Table

All demo accounts can be initialized using `python manage.py seed_demo --reset`.

| Role | Username | Password | Details / Profile Attributes |
| :--- | :--- | :--- | :--- |
| **Placement Admin** | `admin` | `Admin@123` | Superuser & Placement Staff |
| **Recruiter 1** | `recruiter1` | `Recruit@123` | **TechNova Solutions** (Status: **APPROVED**), multiple active postings |
| **Recruiter 2** | `recruiter2` | `Recruit@123` | **Apex Dynamics** (Status: **PENDING**), awaiting verification |
| **Student 1** | `student1` | `Student@123` | CSE, CGPA **8.95**, Batch **2026** (Eligible for all CSE/IT roles) |
| **Student 2** | `student2` | `Student@123` | ECE, CGPA **7.80**, Batch **2026** (Hardware/Embedded and general roles) |
| **Student 3** | `student3` | `Student@123` | MECH, CGPA **6.50**, Batch **2025** (Older batch, core branch) |
| **Student 4** | `student4` | `Student@123` | IT, CGPA **9.20**, Batch **2026** (Top-tier academic profile) |
| **Student 5** | `student5` | `Student@123` | AI&DS, CGPA **8.10**, Batch **2027** (Junior batch; tests graduation year gating) |
| **Student 6** | `student6` | `Student@123` | CIVIL, CGPA **6.20**, Batch **2026** (Tests branch and CGPA gating) |

---

## Local Setup & Quickstart

### Prerequisites
- Python 3.11 or higher
- Git and virtual environment tools (`venv`)

### Setup Instructions

1 . 1. **Clone the Repository**: ```bash git clone https://github.com/Aniket-Ahlu/campus-placement-portal.git cd campus-placement-portal ```
2. **Create and Activate a Virtual Environment**:
   - On Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - On macOS / Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Database Migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Seed Demo Data**:
   ```bash
   python manage.py seed_demo --reset
   ```

6. **Start the Development Server**:
   ```bash
   python manage.py runserver
   ```

7. **Access the Portal**:
   - Web Application: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - Admin Console: [http://127.0.0.1:8000/placement-admin/](http://127.0.0.1:8000/placement-admin/)
   - Django Admin: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## Running Tests

The test suite covers eligibility logic, server-side apply enforcement, posting visibility rules, role isolation, batch status updates, and administrative audit logging:

```bash
python manage.py test
```

Expected output:
```text
Ran 22 tests in ...s

OK
```

---

## Folder Structure

```text
campus_placement_portal/
├── config/
│   ├── __init__.py
│   ├── settings.py           # Project settings, AUTH_USER_MODEL, template/static configs
│   ├── urls.py               # Main URL router and custom error handlers
│   ├── wsgi.py
│   └── asgi.py
├── core/
│   ├── models.py             # Academic Branch model
│   ├── decorators.py         # Role guards: @student_required, @recruiter_required, @admin_required
│   ├── eligibility.py        # Centralized check_eligibility() function
│   ├── context_processors.py # portal_context supplying role info and badge counts
│   ├── views.py              # Landing page, dashboard_redirect, 403/404/500 handlers
│   ├── urls.py
│   ├── tests.py              # Unit, permission, and role page smoke tests (22 tests)
│   └── management/commands/
│       └── seed_demo.py      # Idempotent demo database seeder (--reset flag)
├── accounts/
│   ├── models.py             # Custom User model (role choices) & StudentProfile
│   ├── forms.py              # Registration and profile edit forms
│   ├── views.py              # Auth views, student dashboard, profile view/edit
│   └── urls.py
├── companies/
│   ├── models.py             # Company model (PENDING/APPROVED/REJECTED)
│   ├── forms.py              # Company edit form
│   ├── views.py              # Recruiter company management
│   └── urls.py
├── jobs/
│   ├── models.py             # JobPosting model (eligibility criteria, status, is_open)
│   ├── forms.py              # Job posting creation/edit form
│   ├── views.py              # Browse, posting detail, recruiter postings management
│   └── urls.py
├── applications/
│   ├── models.py             # Application and ApplicationStatusHistory models
│   ├── views.py              # Apply, my applications, visual timeline, status feed API, batch updates
│   └── urls.py
├── placement_admin/
│   ├── models.py             # Append-only AdminActionLog model
│   ├── admin.py              # Read-only AdminActionLog admin registration
│   ├── views.py              # Admin dashboard, company/posting queues, audit logs, users list
│   └── urls.py
├── static/
│   ├── css/
│   │   └── custom.css        # Indigo theme variables, timeline styles, badge styling
│   └── js/
│       └── status_feed.js    # 15s real-time fetch polling & DOM status updater
├── templates/
│   ├── base.html             # Main layout, role-specific navbars, alerts container, footer
│   ├── 403.html              # Custom Forbidden error page
│   ├── 404.html              # Custom Not Found error page
│   ├── 500.html              # Custom Server Error page
│   ├── core/landing.html
│   ├── accounts/
│   ├── companies/
│   ├── jobs/
│   ├── applications/
│   └── placement_admin/
├── requirements.txt          # Pinned Django dependency
└── README.md
```

