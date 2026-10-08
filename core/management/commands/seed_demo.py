from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Branch
from accounts.models import StudentProfile
from companies.models import Company
from jobs.models import JobPosting
from applications.models import Application, ApplicationStatusHistory
from placement_admin.models import AdminActionLog

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds demo data for Campus Placement & Internship Portal (Idempotent, --reset supported)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Wipe all existing data before seeding.',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        if reset:
            self.stdout.write(self.style.WARNING("Resetting existing portal data..."))
            AdminActionLog.objects.all().delete()
            ApplicationStatusHistory.objects.all().delete()
            Application.objects.all().delete()
            JobPosting.objects.all().delete()
            Company.objects.all().delete()
            StudentProfile.objects.all().delete()
            User.objects.all().delete()
            Branch.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing data wiped."))

        self.stdout.write("Seeding academic branches...")
        branches_data = [
            ('Computer Science & Engineering', 'CSE'),
            ('Information Technology', 'IT'),
            ('Electronics & Communication Engineering', 'ECE'),
            ('Electrical & Electronics Engineering', 'EEE'),
            ('Mechanical Engineering', 'MECH'),
            ('Civil Engineering', 'CIVIL'),
            ('Artificial Intelligence & Data Science', 'AI&DS'),
        ]
        branches = {}
        for name, code in branches_data:
            branch, _ = Branch.objects.get_or_create(name=name, defaults={'code': code})
            branches[code] = branch

        self.stdout.write("Seeding placement admin...")
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@placement.edu',
                'role': User.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin.set_password('Admin@123')
        admin.role = User.ROLE_ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        self.stdout.write("Seeding recruiters and companies...")
        # Recruiter 1: TechNova Solutions (APPROVED)
        recruiter1, _ = User.objects.get_or_create(
            username='recruiter1',
            defaults={
                'email': 'hr@technova.io',
                'role': User.ROLE_RECRUITER,
            }
        )
        recruiter1.set_password('Recruit@123')
        recruiter1.role = User.ROLE_RECRUITER
        recruiter1.save()

        company1, _ = Company.objects.get_or_create(
            owner=recruiter1,
            defaults={
                'name': 'TechNova Solutions',
                'website': 'https://technova.io',
                'industry': 'Software & Cloud Services',
                'location': 'Bengaluru, India',
                'description': 'Pioneering global SaaS platforms, distributed computing systems, and intelligent enterprise automation.',
                'status': Company.STATUS_APPROVED,
            }
        )
        company1.status = Company.STATUS_APPROVED
        company1.save()

        # Recruiter 2: Apex Dynamics (PENDING)
        recruiter2, _ = User.objects.get_or_create(
            username='recruiter2',
            defaults={
                'email': 'talent@apexdynamics.ai',
                'role': User.ROLE_RECRUITER,
            }
        )
        recruiter2.set_password('Recruit@123')
        recruiter2.role = User.ROLE_RECRUITER
        recruiter2.save()

        company2, _ = Company.objects.get_or_create(
            owner=recruiter2,
            defaults={
                'name': 'Apex Dynamics',
                'website': 'https://apexdynamics.ai',
                'industry': 'Robotics & Autonomous Systems',
                'location': 'Hyderabad, India',
                'description': 'Building state-of-the-art warehouse robotics and computer-vision powered autonomous guided vehicles.',
                'status': Company.STATUS_PENDING,
            }
        )

        self.stdout.write("Seeding students and profiles...")
        students_data = [
            ('student1', 'student1@college.edu', 'Aarav Sharma', 'CSE', Decimal('8.95'), 2026, 'https://drive.google.com/aarav_resume.pdf', '+91 9876543210'),
            ('student2', 'student2@college.edu', 'Priya Patel', 'ECE', Decimal('7.80'), 2026, 'https://drive.google.com/priya_resume.pdf', '+91 9876543211'),
            ('student3', 'student3@college.edu', 'Rohan Verma', 'MECH', Decimal('6.50'), 2025, 'https://drive.google.com/rohan_resume.pdf', '+91 9876543212'),
            ('student4', 'student4@college.edu', 'Ananya Iyer', 'IT', Decimal('9.20'), 2026, 'https://drive.google.com/ananya_resume.pdf', '+91 9876543213'),
            ('student5', 'student5@college.edu', 'Kabir Sen', 'AI&DS', Decimal('8.10'), 2027, 'https://drive.google.com/kabir_resume.pdf', '+91 9876543214'),
            ('student6', 'student6@college.edu', 'Sneha Roy', 'CIVIL', Decimal('6.20'), 2026, 'https://drive.google.com/sneha_resume.pdf', '+91 9876543215'),
        ]

        students = {}
        for username, email, full_name, branch_code, cgpa, grad_year, resume, phone in students_data:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'role': User.ROLE_STUDENT}
            )
            user.set_password('Student@123')
            user.role = User.ROLE_STUDENT
            user.save()
            students[username] = user

            StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    'full_name': full_name,
                    'branch': branches[branch_code],
                    'cgpa': cgpa,
                    'graduation_year': grad_year,
                    'resume_link': resume,
                    'phone': phone,
                }
            )

        self.stdout.write("Seeding job postings...")
        today = timezone.now().date()
        postings = []

        # 1. TechNova - SDE Backend (APPROVED)
        p1, _ = JobPosting.objects.get_or_create(
            company=company1,
            title='Software Development Engineer (Backend)',
            defaults={
                'description': 'Join our core platform engineering team building low-latency microservices with Python and Go.',
                'job_type': JobPosting.JOB_TYPE_FULLTIME,
                'location': 'Bengaluru (Hybrid)',
                'salary_or_stipend': '18 LPA',
                'min_cgpa': Decimal('7.50'),
                'graduation_year': 2026,
                'deadline': today + timedelta(days=30),
                'status': JobPosting.STATUS_APPROVED,
                'is_open': True,
            }
        )
        p1.allowed_branches.set([branches['CSE'], branches['IT']])
        postings.append(p1)

        # 2. TechNova - Data Science & ML Intern (APPROVED)
        p2, _ = JobPosting.objects.get_or_create(
            company=company1,
            title='Data Science & ML Intern',
            defaults={
                'description': 'Develop NLP and deep learning models for unstructured text analysis and forecasting pipelines.',
                'job_type': JobPosting.JOB_TYPE_INTERNSHIP,
                'location': 'Bengaluru (On-site)',
                'salary_or_stipend': '₹45,000 / month',
                'min_cgpa': Decimal('8.00'),
                'graduation_year': 2026,
                'deadline': today + timedelta(days=20),
                'status': JobPosting.STATUS_APPROVED,
                'is_open': True,
            }
        )
        p2.allowed_branches.set([branches['CSE'], branches['IT'], branches['AI&DS']])
        postings.append(p2)

        # 3. TechNova - DevOps & Cloud Engineer (APPROVED, All branches)
        p3, _ = JobPosting.objects.get_or_create(
            company=company1,
            title='DevOps & Cloud Engineer',
            defaults={
                'description': 'Build automated CI/CD pipelines, manage Kubernetes clusters, and optimize cloud infrastructure.',
                'job_type': JobPosting.JOB_TYPE_FULLTIME,
                'location': 'Remote',
                'salary_or_stipend': '14 LPA',
                'min_cgpa': Decimal('7.00'),
                'graduation_year': 2026,
                'deadline': today + timedelta(days=45),
                'status': JobPosting.STATUS_APPROVED,
                'is_open': True,
            }
        )
        p3.allowed_branches.clear()  # open to all
        postings.append(p3)

        # 4. TechNova - Embedded Systems Trainee (APPROVED)
        p4, _ = JobPosting.objects.get_or_create(
            company=company1,
            title='Embedded Systems Trainee',
            defaults={
                'description': 'Firmware development in C/C++ on ARM Cortex microcontrollers and IoT communication stacks.',
                'job_type': JobPosting.JOB_TYPE_FULLTIME,
                'location': 'Bengaluru',
                'salary_or_stipend': '10 LPA',
                'min_cgpa': Decimal('7.20'),
                'graduation_year': 2026,
                'deadline': today + timedelta(days=25),
                'status': JobPosting.STATUS_APPROVED,
                'is_open': True,
            }
        )
        p4.allowed_branches.set([branches['ECE'], branches['EEE']])
        postings.append(p4)

        # 5. TechNova - Product Management Intern (APPROVED, open to all batches & branches)
        p5, _ = JobPosting.objects.get_or_create(
            company=company1,
            title='Product Management Intern',
            defaults={
                'description': 'Conduct market research, write user stories, and collaborate with engineering on feature rollouts.',
                'job_type': JobPosting.JOB_TYPE_INTERNSHIP,
                'location': 'Hybrid (Bengaluru)',
                'salary_or_stipend': '₹30,000 / month',
                'min_cgpa': Decimal('6.00'),
                'graduation_year': None,
                'deadline': today + timedelta(days=15),
                'status': JobPosting.STATUS_APPROVED,
                'is_open': True,
            }
        )
        p5.allowed_branches.clear()
        postings.append(p5)

        # 6. TechNova - Frontend Engineering Fellow (PENDING approval)
        p6, _ = JobPosting.objects.get_or_create(
            company=company1,
            title='Frontend Engineering Fellow',
            defaults={
                'description': 'Craft pixel-perfect responsive web applications using modern web standards.',
                'job_type': JobPosting.JOB_TYPE_FULLTIME,
                'location': 'Bengaluru',
                'salary_or_stipend': '12 LPA',
                'min_cgpa': Decimal('7.00'),
                'graduation_year': 2026,
                'deadline': today + timedelta(days=35),
                'status': JobPosting.STATUS_PENDING,
                'is_open': True,
            }
        )
        p6.allowed_branches.set([branches['CSE'], branches['IT']])
        postings.append(p6)

        # 7. TechNova - Blockchain Research Intern (REJECTED by admin)
        p7, _ = JobPosting.objects.get_or_create(
            company=company1,
            title='Blockchain Research Intern',
            defaults={
                'description': 'Research on distributed ledger consensus and smart contract security.',
                'job_type': JobPosting.JOB_TYPE_INTERNSHIP,
                'location': 'Remote',
                'salary_or_stipend': '₹50,000 / month',
                'min_cgpa': Decimal('8.50'),
                'graduation_year': 2026,
                'deadline': today + timedelta(days=10),
                'status': JobPosting.STATUS_REJECTED,
                'rejection_reason': 'Crypto and Web3 roles are currently not authorized under campus placement policy.',
                'is_open': True,
            }
        )
        p7.allowed_branches.set([branches['CSE']])
        postings.append(p7)

        # 8. TechNova - Past Summer Internship 2025 (Expired & closed)
        p8, _ = JobPosting.objects.get_or_create(
            company=company1,
            title='Past Summer Internship 2025',
            defaults={
                'description': 'Previous year summer training cohort.',
                'job_type': JobPosting.JOB_TYPE_INTERNSHIP,
                'location': 'Bengaluru',
                'salary_or_stipend': '₹25,000 / month',
                'min_cgpa': Decimal('6.50'),
                'graduation_year': 2025,
                'deadline': today - timedelta(days=60),
                'status': JobPosting.STATUS_APPROVED,
                'is_open': False,
            }
        )
        postings.append(p8)

        # 9. Apex Dynamics - Robotics Systems Engineer (PENDING company)
        p9, _ = JobPosting.objects.get_or_create(
            company=company2,
            title='Robotics Systems Engineer',
            defaults={
                'description': 'Sensor fusion, ROS2 architecture, and motion planning for mobile warehouse robots.',
                'job_type': JobPosting.JOB_TYPE_FULLTIME,
                'location': 'Hyderabad',
                'salary_or_stipend': '15 LPA',
                'min_cgpa': Decimal('7.50'),
                'graduation_year': 2026,
                'deadline': today + timedelta(days=40),
                'status': JobPosting.STATUS_PENDING,
                'is_open': True,
            }
        )
        p9.allowed_branches.set([branches['MECH'], branches['ECE'], branches['CSE']])
        postings.append(p9)

        # 10. Apex Dynamics - Computer Vision Intern (PENDING company)
        p10, _ = JobPosting.objects.get_or_create(
            company=company2,
            title='Computer Vision Intern',
            defaults={
                'description': 'Real-time object detection and SLAM algorithm implementation.',
                'job_type': JobPosting.JOB_TYPE_INTERNSHIP,
                'location': 'Hyderabad',
                'salary_or_stipend': '₹40,000 / month',
                'min_cgpa': Decimal('8.00'),
                'graduation_year': 2026,
                'deadline': today + timedelta(days=20),
                'status': JobPosting.STATUS_PENDING,
                'is_open': True,
            }
        )
        p10.allowed_branches.set([branches['CSE'], branches['AI&DS']])
        postings.append(p10)

        self.stdout.write("Seeding student applications & timeline status histories...")
        app_configs = [
            (students['student1'], p1, Application.STATUS_OFFERED, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted by candidate.'),
                (Application.STATUS_APPLIED, Application.STATUS_UNDER_REVIEW, 'Profile passed preliminary ATS screening.'),
                (Application.STATUS_UNDER_REVIEW, Application.STATUS_SHORTLISTED, 'Shortlisted based on strong coding credentials.'),
                (Application.STATUS_SHORTLISTED, Application.STATUS_INTERVIEW, 'Technical round 1 and round 2 scheduled.'),
                (Application.STATUS_INTERVIEW, Application.STATUS_OFFERED, 'Exceptional performance in system design. Offer extended!'),
            ]),
            (students['student4'], p1, Application.STATUS_INTERVIEW, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
                (Application.STATUS_APPLIED, Application.STATUS_UNDER_REVIEW, 'Resume under hiring team review.'),
                (Application.STATUS_UNDER_REVIEW, Application.STATUS_SHORTLISTED, 'Shortlisted for online assessment.'),
                (Application.STATUS_SHORTLISTED, Application.STATUS_INTERVIEW, 'Cleared assessment with 98% percentile. Interview invited.'),
            ]),
            (students['student2'], p3, Application.STATUS_SHORTLISTED, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
                (Application.STATUS_APPLIED, Application.STATUS_UNDER_REVIEW, 'Reviewing cloud portfolio and GitHub projects.'),
                (Application.STATUS_UNDER_REVIEW, Application.STATUS_SHORTLISTED, 'Selected for technical evaluation round.'),
            ]),
            (students['student1'], p2, Application.STATUS_UNDER_REVIEW, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
                (Application.STATUS_APPLIED, Application.STATUS_UNDER_REVIEW, 'Under data science panel review.'),
            ]),
            (students['student4'], p2, Application.STATUS_APPLIED, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
            ]),
            (students['student2'], p4, Application.STATUS_OFFERED, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
                (Application.STATUS_APPLIED, Application.STATUS_UNDER_REVIEW, 'Under hardware group review.'),
                (Application.STATUS_UNDER_REVIEW, Application.STATUS_SHORTLISTED, 'Shortlisted for lab round.'),
                (Application.STATUS_SHORTLISTED, Application.STATUS_INTERVIEW, 'Technical interview completed.'),
                (Application.STATUS_INTERVIEW, Application.STATUS_OFFERED, 'Offer released for Embedded Systems Trainee role.'),
            ]),
            (students['student5'], p2, Application.STATUS_REJECTED, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
                (Application.STATUS_APPLIED, Application.STATUS_UNDER_REVIEW, 'Under evaluation.'),
                (Application.STATUS_UNDER_REVIEW, Application.STATUS_REJECTED, 'Candidate graduation batch is 2027, role required 2026.'),
            ]),
            (students['student1'], p5, Application.STATUS_WITHDRAWN, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
                (Application.STATUS_APPLIED, Application.STATUS_UNDER_REVIEW, 'Under product management review.'),
                (Application.STATUS_UNDER_REVIEW, Application.STATUS_WITHDRAWN, 'Candidate withdrew to accept full-time SDE offer.'),
            ]),
            (students['student3'], p5, Application.STATUS_SHORTLISTED, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
                (Application.STATUS_APPLIED, Application.STATUS_UNDER_REVIEW, 'Under review.'),
                (Application.STATUS_UNDER_REVIEW, Application.STATUS_SHORTLISTED, 'Shortlisted for group discussion round.'),
            ]),
            (students['student6'], p5, Application.STATUS_APPLIED, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
            ]),
            (students['student2'], p5, Application.STATUS_REJECTED, [
                ('NONE', Application.STATUS_APPLIED, 'Application submitted.'),
                (Application.STATUS_APPLIED, Application.STATUS_REJECTED, 'Position filled / candidate focused on core domain.'),
            ]),
        ]

        for student_user, posting_obj, final_st, history_records in app_configs:
            app, _ = Application.objects.get_or_create(
                student=student_user,
                posting=posting_obj,
                defaults={'status': final_st}
            )
            app.status = final_st
            app.save()

            if not app.status_history.exists():
                for old_s, new_s, note in history_records:
                    changed_by = student_user if new_s in [Application.STATUS_APPLIED, Application.STATUS_WITHDRAWN] else recruiter1
                    ApplicationStatusHistory.objects.create(
                        application=app,
                        old_status=old_s,
                        new_status=new_s,
                        changed_by=changed_by,
                        note=note
                    )

        self.stdout.write("Seeding audit action logs...")
        audit_entries = [
            (admin, AdminActionLog.ACTION_APPROVED, AdminActionLog.TARGET_COMPANY, company1.id, company1.name, 'Approved after verifying corporate registration and GSTIN credentials.'),
            (admin, AdminActionLog.ACTION_APPROVED, AdminActionLog.TARGET_JOB_POSTING, p1.id, f"{p1.title} ({company1.name})", 'Approved - Compensation and eligibility comply with campus placement tier-1 standards.'),
            (admin, AdminActionLog.ACTION_APPROVED, AdminActionLog.TARGET_JOB_POSTING, p2.id, f"{p2.title} ({company1.name})", 'Approved - Internship stipend adheres to university policy.'),
            (admin, AdminActionLog.ACTION_APPROVED, AdminActionLog.TARGET_JOB_POSTING, p3.id, f"{p3.title} ({company1.name})", 'Approved - Open to all engineering branches.'),
            (admin, AdminActionLog.ACTION_APPROVED, AdminActionLog.TARGET_JOB_POSTING, p4.id, f"{p4.title} ({company1.name})", 'Approved - Core hardware posting for ECE/EEE.'),
            (admin, AdminActionLog.ACTION_APPROVED, AdminActionLog.TARGET_JOB_POSTING, p5.id, f"{p5.title} ({company1.name})", 'Approved - PM internship.'),
            (admin, AdminActionLog.ACTION_REJECTED, AdminActionLog.TARGET_JOB_POSTING, p7.id, f"{p7.title} ({company1.name})", 'Crypto and Web3 roles are currently not authorized under campus placement policy.'),
        ]

        for adm, action, t_type, t_id, t_label, reason in audit_entries:
            AdminActionLog.objects.get_or_create(
                target_type=t_type,
                target_id=t_id,
                action=action,
                defaults={
                    'admin_user': adm,
                    'admin_id': adm.id,
                    'admin_username': adm.username,
                    'target_label': t_label,
                    'reason': reason,
                }
            )

        self.stdout.write(self.style.SUCCESS("Demo database successfully seeded!"))
