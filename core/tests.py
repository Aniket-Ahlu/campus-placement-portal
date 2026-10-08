from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.models import Branch
from core.eligibility import check_eligibility
from accounts.models import StudentProfile
from companies.models import Company
from jobs.models import JobPosting
from applications.models import Application, ApplicationStatusHistory
from placement_admin.models import AdminActionLog

User = get_user_model()


class BasePortalTestCase(TestCase):
    def setUp(self):
        # Academic Branches
        self.cse = Branch.objects.create(name='Computer Science & Engineering', code='CSE')
        self.it = Branch.objects.create(name='Information Technology', code='IT')
        self.mech = Branch.objects.create(name='Mechanical Engineering', code='MECH')

        # Admin
        self.admin = User.objects.create_superuser(
            username='test_admin',
            email='admin@test.edu',
            password='Password@123',
            role=User.ROLE_ADMIN
        )

        # Recruiter 1 with Approved Company
        self.recruiter1 = User.objects.create_user(
            username='recruiter1',
            email='recruiter1@company1.com',
            password='Password@123',
            role=User.ROLE_RECRUITER
        )
        self.company1 = Company.objects.create(
            owner=self.recruiter1,
            name='Alpha Corp',
            website='https://alpha.com',
            industry='Technology',
            location='Bengaluru',
            description='Tech solutions',
            status=Company.STATUS_APPROVED
        )

        # Recruiter 2 with Pending Company
        self.recruiter2 = User.objects.create_user(
            username='recruiter2',
            email='recruiter2@company2.com',
            password='Password@123',
            role=User.ROLE_RECRUITER
        )
        self.company2 = Company.objects.create(
            owner=self.recruiter2,
            name='Beta Ventures',
            website='https://beta.com',
            industry='Finance',
            location='Mumbai',
            description='Financial services',
            status=Company.STATUS_PENDING
        )

        # Eligible Student
        self.student_eligible = User.objects.create_user(
            username='eligible_student',
            email='student1@test.edu',
            password='Password@123',
            role=User.ROLE_STUDENT
        )
        self.profile_eligible = StudentProfile.objects.create(
            user=self.student_eligible,
            full_name='Eligible Candidate',
            branch=self.cse,
            cgpa=Decimal('8.50'),
            graduation_year=2026,
            resume_link='https://example.com/resume.pdf',
            phone='1234567890'
        )

        # Ineligible Student (Low CGPA, different branch, different batch)
        self.student_ineligible = User.objects.create_user(
            username='ineligible_student',
            email='student2@test.edu',
            password='Password@123',
            role=User.ROLE_STUDENT
        )
        self.profile_ineligible = StudentProfile.objects.create(
            user=self.student_ineligible,
            full_name='Ineligible Candidate',
            branch=self.mech,
            cgpa=Decimal('6.20'),
            graduation_year=2025,
            resume_link='https://example.com/resume2.pdf',
            phone='1234567891'
        )

        # Standard Approved Job Posting
        self.posting_approved = JobPosting.objects.create(
            company=self.company1,
            title='Software Engineer',
            description='Backend developer role',
            job_type=JobPosting.JOB_TYPE_FULLTIME,
            location='Bengaluru',
            salary_or_stipend='15 LPA',
            min_cgpa=Decimal('7.50'),
            graduation_year=2026,
            deadline=timezone.now().date() + timedelta(days=30),
            status=JobPosting.STATUS_APPROVED,
            is_open=True
        )
        self.posting_approved.allowed_branches.add(self.cse, self.it)


class EligibilityFunctionTests(BasePortalTestCase):
    """1. Tests covering eligibility function: CGPA, branch, deadline, duplicate, grad year, profile completeness."""

    def test_eligible_candidate_passes(self):
        reasons = check_eligibility(self.profile_eligible, self.posting_approved)
        self.assertEqual(len(reasons), 0, "Eligible candidate should have zero failure reasons.")

    def test_cgpa_failure(self):
        # Create student with matching branch/year but low CGPA
        user = User.objects.create_user(username='low_cgpa', password='Password@123', role=User.ROLE_STUDENT)
        profile = StudentProfile.objects.create(
            user=user, full_name='Low CGPA Student', branch=self.cse,
            cgpa=Decimal('6.80'), graduation_year=2026, resume_link='https://example.com/r.pdf'
        )
        reasons = check_eligibility(profile, self.posting_approved)
        self.assertTrue(any("your CGPA is 6.80 but this role requires a minimum of 7.50" in r for r in reasons))

    def test_branch_failure(self):
        # Candidate is MECH, posting requires CSE or IT
        reasons = check_eligibility(self.profile_ineligible, self.posting_approved)
        self.assertTrue(any("Your branch (Mechanical Engineering) is not eligible" in r for r in reasons))

    def test_deadline_passed_failure(self):
        expired_posting = JobPosting.objects.create(
            company=self.company1,
            title='Expired Role',
            description='Past role',
            salary_or_stipend='10 LPA',
            min_cgpa=Decimal('6.00'),
            deadline=timezone.now().date() - timedelta(days=1),
            status=JobPosting.STATUS_APPROVED,
            is_open=True
        )
        reasons = check_eligibility(self.profile_eligible, expired_posting)
        self.assertTrue(any("deadline" in r.lower() and "passed" in r.lower() for r in reasons))

    def test_graduation_year_failure(self):
        # Posting requires 2026, profile is 2025
        reasons = check_eligibility(self.profile_ineligible, self.posting_approved)
        self.assertTrue(any("only open for 2026 graduates" in r for r in reasons))

    def test_duplicate_application_failure(self):
        # Apply once
        Application.objects.create(
            student=self.student_eligible,
            posting=self.posting_approved,
            status=Application.STATUS_APPLIED
        )
        reasons = check_eligibility(self.profile_eligible, self.posting_approved)
        self.assertTrue(any("already applied" in r.lower() for r in reasons))

    def test_incomplete_profile_failure(self):
        user_inc = User.objects.create_user(username='inc_user', password='Password@123', role=User.ROLE_STUDENT)
        profile_inc = StudentProfile.objects.create(user=user_inc)  # missing required fields
        reasons = check_eligibility(profile_inc, self.posting_approved)
        self.assertTrue(any("incomplete" in r.lower() for r in reasons))


class ApplyViewGatingTests(BasePortalTestCase):
    """2. Apply view blocks ineligible students server-side with notice."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_ineligible_student_apply_blocked(self):
        self.client.login(username='ineligible_student', password='Password@123')
        url = reverse('applications:apply', kwargs={'posting_id': self.posting_approved.id})

        # Attempt to POST application
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)

        # Confirm no Application was created
        app_exists = Application.objects.filter(
            student=self.student_ineligible,
            posting=self.posting_approved
        ).exists()
        self.assertFalse(app_exists, "Ineligible student application must NOT be created.")

    def test_eligible_student_apply_succeeds(self):
        self.client.login(username='eligible_student', password='Password@123')
        url = reverse('applications:apply', kwargs={'posting_id': self.posting_approved.id})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # Verify application created with APPLIED status and status history
        app = Application.objects.filter(
            student=self.student_eligible,
            posting=self.posting_approved
        ).first()
        self.assertIsNotNone(app)
        self.assertEqual(app.status, Application.STATUS_APPLIED)
        self.assertTrue(app.status_history.filter(new_status=Application.STATUS_APPLIED).exists())


class UnapprovedPostingsVisibilityTests(BasePortalTestCase):
    """3. Unapproved postings are invisible and return 404 to students."""

    def setUp(self):
        super().setUp()
        self.client = Client()

        # Unapproved pending posting
        self.posting_pending = JobPosting.objects.create(
            company=self.company1,
            title='Pending QA Role',
            description='QA Tester',
            salary_or_stipend='8 LPA',
            min_cgpa=Decimal('6.00'),
            deadline=timezone.now().date() + timedelta(days=20),
            status=JobPosting.STATUS_PENDING,
            is_open=True
        )

        # Rejected posting
        self.posting_rejected = JobPosting.objects.create(
            company=self.company1,
            title='Rejected Role',
            description='Archived',
            salary_or_stipend='8 LPA',
            min_cgpa=Decimal('6.00'),
            deadline=timezone.now().date() + timedelta(days=20),
            status=JobPosting.STATUS_REJECTED,
            is_open=True
        )

        # Posting of unapproved/pending company
        self.posting_unapproved_company = JobPosting.objects.create(
            company=self.company2,  # company2 is PENDING
            title='Financial Analyst',
            description='Finance role',
            salary_or_stipend='12 LPA',
            min_cgpa=Decimal('6.00'),
            deadline=timezone.now().date() + timedelta(days=20),
            status=JobPosting.STATUS_APPROVED,  # Even if posting marked approved, company is pending
            is_open=True
        )

    def test_browse_postings_hides_unapproved_from_students(self):
        self.client.login(username='eligible_student', password='Password@123')
        response = self.client.get(reverse('jobs:browse'))
        self.assertEqual(response.status_code, 200)

        # Posting list should contain approved posting only
        postings = list(response.context['page_obj'])
        self.assertIn(self.posting_approved, postings)
        self.assertNotIn(self.posting_pending, postings)
        self.assertNotIn(self.posting_rejected, postings)
        self.assertNotIn(self.posting_unapproved_company, postings)

    def test_direct_url_to_unapproved_posting_returns_404_for_student(self):
        self.client.login(username='eligible_student', password='Password@123')

        # Direct access to pending posting
        resp_pending = self.client.get(reverse('jobs:detail', kwargs={'pk': self.posting_pending.id}))
        self.assertEqual(resp_pending.status_code, 404)

        # Direct access to rejected posting
        resp_rejected = self.client.get(reverse('jobs:detail', kwargs={'pk': self.posting_rejected.id}))
        self.assertEqual(resp_rejected.status_code, 404)

        # Direct access to posting with pending company
        resp_unapp_comp = self.client.get(reverse('jobs:detail', kwargs={'pk': self.posting_unapproved_company.id}))
        self.assertEqual(resp_unapp_comp.status_code, 404)


class RoleIsolationAndPermissionsTests(BasePortalTestCase):
    """4. Role isolation: cross-role and cross-user object-level security."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_student_cannot_access_recruiter_and_admin_urls(self):
        self.client.login(username='eligible_student', password='Password@123')

        # Recruiter URL
        resp_rec = self.client.get(reverse('jobs:recruiter_dashboard'))
        self.assertEqual(resp_rec.status_code, 403)

        # Admin URL
        resp_adm = self.client.get(reverse('placement_admin:dashboard'))
        self.assertEqual(resp_adm.status_code, 403)

    def test_recruiter_cannot_access_student_and_admin_urls(self):
        self.client.login(username='recruiter1', password='Password@123')

        # Student URL
        resp_stu = self.client.get(reverse('accounts:student_dashboard'))
        self.assertEqual(resp_stu.status_code, 403)

        # Admin URL
        resp_adm = self.client.get(reverse('placement_admin:dashboard'))
        self.assertEqual(resp_adm.status_code, 403)

    def test_recruiter_cannot_view_another_company_applicants(self):
        # Recruiter 2 tries to view applicants for Recruiter 1's company posting
        self.client.login(username='recruiter2', password='Password@123')
        url = reverse('applications:recruiter_applicants', kwargs={'posting_id': self.posting_approved.id})
        response = self.client.get(url)
        # Should return 404 because get_object_or_404 filters by company__owner=request.user
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_view_another_student_application(self):
        # Create application for eligible_student
        app = Application.objects.create(
            student=self.student_eligible,
            posting=self.posting_approved,
            status=Application.STATUS_APPLIED
        )

        # Log in as ineligible_student and try to view it
        self.client.login(username='ineligible_student', password='Password@123')
        resp = self.client.get(reverse('applications:detail', kwargs={'pk': app.id}))
        self.assertEqual(resp.status_code, 404)


class BatchStatusUpdateTests(BasePortalTestCase):
    """5. Batch status update including an invalid transition."""

    def setUp(self):
        super().setUp()
        self.client = Client()

        # Application 1: APPLIED state (can transition to UNDER_REVIEW)
        self.app1 = Application.objects.create(
            student=self.student_eligible,
            posting=self.posting_approved,
            status=Application.STATUS_APPLIED
        )

        # Application 2: OFFERED state (final state, CANNOT transition to UNDER_REVIEW)
        self.app2 = Application.objects.create(
            student=self.student_ineligible,
            posting=self.posting_approved,
            status=Application.STATUS_OFFERED
        )

    def test_batch_update_skips_invalid_transitions(self):
        self.client.login(username='recruiter1', password='Password@123')
        url = reverse('applications:recruiter_applicants', kwargs={'posting_id': self.posting_approved.id})

        # Post batch update targeting UNDER_REVIEW for both app1 and app2
        post_data = {
            'batch_update': '1',
            'selected_applicants': [self.app1.id, self.app2.id],
            'target_status': Application.STATUS_UNDER_REVIEW,
            'batch_note': 'Batch screening test'
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Refresh from database
        self.app1.refresh_from_db()
        self.app2.refresh_from_db()

        # App 1 should be updated to UNDER_REVIEW
        self.assertEqual(self.app1.status, Application.STATUS_UNDER_REVIEW)
        # History recorded for App 1
        self.assertTrue(self.app1.status_history.filter(new_status=Application.STATUS_UNDER_REVIEW).exists())

        # App 2 was in OFFERED (final), so transition should be skipped
        self.assertEqual(self.app2.status, Application.STATUS_OFFERED)

        # Check flash message reporting skip
        messages = [m.message for m in response.context['messages']]
        self.assertTrue(any("1 updated, 1 skipped: invalid transition" in m for m in messages))


class AdminModerationAndAuditLogTests(BasePortalTestCase):
    """6. Audit log creation with the admin id on approve/reject."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.login(username='test_admin', password='Password@123')

    def test_admin_approve_company_creates_audit_log(self):
        # company2 is PENDING
        url = reverse('placement_admin:moderate_company', kwargs={'pk': self.company2.id})
        response = self.client.post(url, {'action': 'APPROVE', 'reason': 'Verified corporate documents.'})
        self.assertEqual(response.status_code, 302)

        self.company2.refresh_from_db()
        self.assertEqual(self.company2.status, Company.STATUS_APPROVED)

        # Verify Audit Log
        log = AdminActionLog.objects.filter(
            target_type=AdminActionLog.TARGET_COMPANY,
            target_id=self.company2.id,
            action=AdminActionLog.ACTION_APPROVED
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin_id, self.admin.id)
        self.assertEqual(log.admin_username, self.admin.username)
        self.assertEqual(log.target_label, self.company2.name)

    def test_admin_reject_posting_requires_reason_and_creates_log(self):
        # Try rejecting posting without reason -> fails
        url = reverse('placement_admin:moderate_posting', kwargs={'pk': self.posting_approved.id})
        resp_no_reason = self.client.post(url, {'action': 'REJECT', 'reason': ''})
        self.assertEqual(resp_no_reason.status_code, 302)
        self.posting_approved.refresh_from_db()
        self.assertNotEqual(self.posting_approved.status, JobPosting.STATUS_REJECTED)

        # Reject posting WITH reason -> succeeds and writes log
        rejection_reason = "Compensation does not meet university minimum guidelines."
        resp_with_reason = self.client.post(url, {'action': 'REJECT', 'reason': rejection_reason})
        self.assertEqual(resp_with_reason.status_code, 302)

        self.posting_approved.refresh_from_db()
        self.assertEqual(self.posting_approved.status, JobPosting.STATUS_REJECTED)
        self.assertEqual(self.posting_approved.rejection_reason, rejection_reason)

        log = AdminActionLog.objects.filter(
            target_type=AdminActionLog.TARGET_JOB_POSTING,
            target_id=self.posting_approved.id,
            action=AdminActionLog.ACTION_REJECTED
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin_id, self.admin.id)
        self.assertEqual(log.admin_username, self.admin.username)
        self.assertEqual(log.reason, rejection_reason)


class SmokeTestAllRolePages(BasePortalTestCase):
    """Smoke test every role's main pages: all return 200 and render without template errors."""

    def setUp(self):
        super().setUp()
        self.client = Client()

        # Create an application for student1 to view in detail
        self.application = Application.objects.create(
            student=self.student_eligible,
            posting=self.posting_approved,
            status=Application.STATUS_APPLIED
        )
        ApplicationStatusHistory.objects.create(
            application=self.application,
            old_status='NONE',
            new_status=Application.STATUS_APPLIED,
            changed_by=self.student_eligible,
            note='Initial apply'
        )

    def test_public_pages_smoke(self):
        urls = [
            reverse('core:landing'),
            reverse('accounts:login'),
            reverse('accounts:register_student'),
            reverse('accounts:register_recruiter'),
            reverse('jobs:browse'),
            reverse('jobs:detail', kwargs={'pk': self.posting_approved.id}),
        ]
        for u in urls:
            resp = self.client.get(u)
            self.assertEqual(resp.status_code, 200, f"Public page failed: {u}")

    def test_student_pages_smoke(self):
        self.client.login(username='eligible_student', password='Password@123')
        urls = [
            reverse('accounts:student_dashboard'),
            reverse('accounts:student_profile'),
            reverse('applications:my_applications'),
            reverse('applications:detail', kwargs={'pk': self.application.id}),
            reverse('jobs:browse'),
            reverse('jobs:detail', kwargs={'pk': self.posting_approved.id}),
            reverse('applications:apply', kwargs={'posting_id': self.posting_approved.id}),
        ]
        for u in urls:
            resp = self.client.get(u)
            self.assertEqual(resp.status_code, 200, f"Student page failed: {u}")

        # Check status feed JSON endpoint
        feed_resp = self.client.get(reverse('applications:status_feed'))
        self.assertEqual(feed_resp.status_code, 200)
        self.assertIn('applications', feed_resp.json())

    def test_recruiter_pages_smoke(self):
        self.client.login(username='recruiter1', password='Password@123')
        urls = [
            reverse('jobs:recruiter_dashboard'),
            reverse('companies:profile'),
            reverse('jobs:recruiter_postings'),
            reverse('jobs:recruiter_posting_create'),
            reverse('jobs:recruiter_posting_edit', kwargs={'pk': self.posting_approved.id}),
            reverse('applications:recruiter_applicants', kwargs={'posting_id': self.posting_approved.id}),
            reverse('applications:recruiter_applicant_detail', kwargs={'pk': self.application.id}),
        ]
        for u in urls:
            resp = self.client.get(u)
            self.assertEqual(resp.status_code, 200, f"Recruiter page failed: {u}")

    def test_admin_pages_smoke(self):
        self.client.login(username='test_admin', password='Password@123')
        urls = [
            reverse('placement_admin:dashboard'),
            reverse('placement_admin:companies_queue'),
            reverse('placement_admin:postings_queue'),
            reverse('placement_admin:posting_detail', kwargs={'pk': self.posting_approved.id}),
            reverse('placement_admin:audit_logs'),
            reverse('placement_admin:users_list'),
        ]
        for u in urls:
            resp = self.client.get(u)
            self.assertEqual(resp.status_code, 200, f"Admin page failed: {u}")

