from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from django.utils import timezone
import datetime
from .models import Staff, LessonPlan, WeeklyReport, Notification, Community, Student, Sponsor, Report, ReportComment

User = get_user_model()

class AriseWorkflowTests(APITestCase):

    def setUp(self):
        # Create Teacher User & Staff Profile
        self.teacher_user = User.objects.create_user(
            email='teacher@arise.org',
            password='Password123',
            first_name='Morgan',
            last_name='Palata'
        )
        self.teacher_staff = Staff.objects.create(
            user=self.teacher_user,
            full_name='Morgan Palata',
            email='teacher@arise.org',
            account_type='Teacher',
            station='Taonga Primary School'
        )

        # Create Edu-Admin User & Staff Profile
        self.admin_user = User.objects.create_user(
            email='eduadmin@arise.org',
            password='Password123',
            first_name='Katongo',
            last_name='Program'
        )
        self.admin_staff = Staff.objects.create(
            user=self.admin_user,
            full_name='Mrs. Katongo',
            email='eduadmin@arise.org',
            account_type='eduadmin',
            station='Arise Christian School'
        )

        # Helper client credentials setup
        self.teacher_token = AccessToken.for_user(self.teacher_user)
        self.admin_token = AccessToken.for_user(self.admin_user)

    def test_lesson_plan_workflow(self):
        # 1. Create a lesson plan as Teacher
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.teacher_token}')
        post_data = {
            "title": "Grade 1 Math Lesson 1",
            "grade": "Grade 1",
            "subject": "Mathematics",
            "week_number": 1,
            "objectives": "Learn numbers 1 to 10",
            "procedures": "Counting objects aloud",
            "status": "Pending"
        }
        url = reverse('lesson_plans')  # Matches views.py urls mapping
        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'Pending')

        # Verify notification was sent to Edu-Admins
        admin_notifs = Notification.objects.filter(recipient=self.admin_staff)
        self.assertTrue(admin_notifs.exists())
        self.assertIn("New Lesson Plan Submitted", admin_notifs.first().title)

        # 2. View lesson plan as Edu-Admin
        plan_id = response.data['id']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        detail_url = reverse('lesson_plan_detail', kwargs={'pk': plan_id})
        get_response = self.client.get(detail_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        # 3. Approve lesson plan as Edu-Admin
        put_data = {
            "status": "Approved",
            "headmaster_comment": "Excellent structure. Approved!"
        }
        put_response = self.client.put(detail_url, put_data, format='json')
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        self.assertEqual(put_response.data['status'], 'Approved')
        self.assertEqual(put_response.data['headmaster_comment'], 'Excellent structure. Approved!')

        # Verify notification was sent to Teacher
        teacher_notifs = Notification.objects.filter(recipient=self.teacher_staff)
        self.assertTrue(teacher_notifs.exists())
        self.assertIn("Approved", teacher_notifs.first().title)

    def test_weekly_report_lockout(self):
        # 1. Teacher posts weekly report for a future week (valid)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.teacher_token}')
        future_date = (timezone.now() + datetime.timedelta(days=7)).date()
        url = reverse('weekly_reports')
        
        post_data = {
            "week_ending_date": future_date.strftime('%Y-%m-%d'),
            "social_events": "Sports day events went well.",
            "behavioral_issues": "None",
            "health_issues": "None",
            "absenteeism": "None"
        }
        
        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Teacher posts weekly report for a past week (past Friday 3:00 PM) - should be locked
        past_date = (timezone.now() - datetime.timedelta(days=14)).date()
        post_data_past = {
            "week_ending_date": past_date.strftime('%Y-%m-%d'),
            "social_events": "Past social events",
            "behavioral_issues": "None",
            "health_issues": "None",
            "absenteeism": "None"
        }
        
        response_past = self.client.post(url, post_data_past, format='json')
        self.assertEqual(response_past.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("locked", response_past.data['detail'].lower())

    def test_notifications_api(self):
        # Create a notification
        Notification.objects.create(
            recipient=self.teacher_staff,
            title="Test Notice",
            message="Test Msg"
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.teacher_token}')
        url = reverse('notifications')
        
        # Get notifications
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertFalse(response.data[0]['is_read'])

        # Mark all read
        post_response = self.client.post(url)
        self.assertEqual(post_response.status_code, status.HTTP_200_OK)
        
        # Verify read status
        get_response_2 = self.client.get(url)
        self.assertTrue(get_response_2.data[0]['is_read'])

    def test_get_staff_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.teacher_token}')
        url = reverse('complete_staff_profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Morgan Palata')



class ReportHubTests(APITestCase):

    def setUp(self):
        # Create users
        self.cso_user = User.objects.create_user(email='cso@arise.org', password='password123', first_name='CSO', last_name='Staff')
        self.csd_user = User.objects.create_user(email='csd@arise.org', password='password123', first_name='CSD', last_name='Staff')
        self.american_user = User.objects.create_user(email='american@arise.org', password='password123', first_name='US', last_name='Staff')
        self.sponsor_user = User.objects.create_user(email='sponsor@arise.org', password='password123', first_name='Sponsor', last_name='User')

        # Create staff profiles
        self.cso_staff = Staff.objects.create(user=self.cso_user, full_name='CSO Staff', email='cso@arise.org', account_type='CSO')
        self.csd_staff = Staff.objects.create(user=self.csd_user, full_name='CSD Staff', email='csd@arise.org', account_type='CSD')
        self.american_staff = Staff.objects.create(user=self.american_user, full_name='US Staff', email='american@arise.org', account_type='american-staff')

        # Create Sponsor profile
        self.sponsor = Sponsor.objects.create(User=self.sponsor_user, Full_name='Sponsor User', Email='sponsor@arise.org')

        # Create Community
        self.community = Community.objects.create(Name='MacDonald Brown School', CSD=self.csd_staff)

        # Create Student in that community, sponsored by our sponsor, assigned to CSO
        self.student = Student.objects.create(
            Full_name='Banda Mweemba',
            Community_id=self.community,
            CSO_id=self.cso_staff,
            Sponsor_id=self.sponsor,
            Is_sponsored=True
        )

        # Tokens
        self.cso_token = AccessToken.for_user(self.cso_user)
        self.csd_token = AccessToken.for_user(self.csd_user)
        self.american_token = AccessToken.for_user(self.american_user)
        self.sponsor_token = AccessToken.for_user(self.sponsor_user)

    def test_report_generation_and_approval_workflow(self):
        # 1. CSD generates reports for community
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.csd_token}')
        gen_url = reverse('reports')
        gen_data = {
            "community_id": str(self.community.id),
            "term": "Term 1",
            "year": "2026"
        }
        gen_response = self.client.post(gen_url, gen_data, format='json')
        self.assertEqual(gen_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(gen_response.data['generated_count'], 1)

        # Retrieve the report ID
        report = Report.objects.get(Student=self.student, Report_term='Term 1')
        self.assertEqual(report.status, 'Ready to begin')

        # 2. CSO edits report & submits for approval
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.cso_token}')
        detail_url = reverse('report_detail', kwargs={'pk': report.id})
        
        put_data = {
            "Content": "Banda has made outstanding progress in mathematics.",
            "Prayer_request": "Pray for his family's health.",
            "status": "Waiting for Approval"
        }
        put_response = self.client.put(detail_url, put_data, format='json')
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        self.assertEqual(put_response.data['status'], 'Waiting for Approval')

        # Verify CSD received notification
        csd_notif = Notification.objects.filter(recipient=self.csd_staff).first()
        self.assertIsNotNone(csd_notif)
        self.assertIn("Ready for Review", csd_notif.title)

        # 3. CSD approves & assigns American editor
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.csd_token}')
        approve_data = {
            "status": "Waiting for US Approval",
            "american_editor": str(self.american_staff.id)
        }
        approve_response = self.client.put(detail_url, approve_data, format='json')
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data['status'], 'Waiting for US Approval')

        # Verify American editor received notification
        us_notif = Notification.objects.filter(recipient=self.american_staff).first()
        self.assertIsNotNone(us_notif)
        self.assertIn("Awaiting Final US Approval", us_notif.title)

        # 4. American editor approves the report
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.american_token}')
        final_approve_data = {
            "status": "Approved"
        }
        final_response = self.client.put(detail_url, final_approve_data, format='json')
        self.assertEqual(final_response.status_code, status.HTTP_200_OK)
        self.assertEqual(final_response.data['status'], 'Approved')

        # Verify sponsor can now see the report
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.sponsor_token}')
        sponsor_response = self.client.get(gen_url)
        self.assertEqual(sponsor_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(sponsor_response.data), 1)
        self.assertEqual(sponsor_response.data[0]['id'], str(report.id))

    def test_report_commenting(self):
        # Create a report stub directly
        report = Report.objects.create(
            Student=self.student,
            CSO=self.cso_staff,
            CSD=self.csd_staff,
            american_editor=self.american_staff,
            status='Waiting for Approval',
            Report_term='Term 1',
            date_submitted=datetime.date(2026, 1, 1)
        )

        # CSO comments on the report
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.cso_token}')
        comment_url = reverse('report_comment', kwargs={'pk': report.id})
        comment_data = {
            "text": "CSD, could you please review the phrasing of paragraph 2?"
        }
        comment_response = self.client.post(comment_url, comment_data, format='json')
        self.assertEqual(comment_response.status_code, status.HTTP_201_CREATED)

        # Verify CSD and American received comment notifications
        csd_comment_notif = Notification.objects.filter(recipient=self.csd_staff, title__icontains="New Comment").first()
        self.assertIsNotNone(csd_comment_notif)
        self.assertIn("CSO Staff commented", csd_comment_notif.message)

        us_comment_notif = Notification.objects.filter(recipient=self.american_staff, title__icontains="New Comment").first()
        self.assertIsNotNone(us_comment_notif)

    def test_sponsor_student_workflow(self):
        # Create an unsponsored student
        unsponsored_student = Student.objects.create(
            Full_name='Chansa Mulenga',
            Community_id=self.community,
            CSO_id=self.cso_staff,
            Is_sponsored=False
        )
        
        # Sponsor the child
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.sponsor_token}')
        sponsor_url = reverse('sponsor_student', kwargs={'pk': unsponsored_student.id})
        response = self.client.post(sponsor_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify student is now sponsored
        unsponsored_student.refresh_from_db()
        self.assertTrue(unsponsored_student.Is_sponsored)
        self.assertEqual(unsponsored_student.Sponsor_id, self.sponsor)
        
        # Verify notifications sent to CSO, CSD, and American
        cso_notif = Notification.objects.filter(recipient=self.cso_staff, title__icontains="New Student Sponsored").first()
        self.assertIsNotNone(cso_notif)
        
        csd_notif = Notification.objects.filter(recipient=self.csd_staff, title__icontains="New Student Sponsored").first()
        self.assertIsNotNone(csd_notif)
        
        us_notif = Notification.objects.filter(recipient=self.american_staff, title__icontains="New Student Sponsored").first()
        self.assertIsNotNone(us_notif)

    def test_academic_records_sponsor_access(self):
        # Create an unsponsored student
        other_student = Student.objects.create(
            Full_name='Mwelwa Phiri',
            Community_id=self.community,
            CSO_id=self.cso_staff,
            Is_sponsored=False
        )
        
        # Try to access other_student's academic records as our sponsor user -> should be blocked (403)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.sponsor_token}')
        url = reverse('academic_records') + f"?student_id={other_student.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to access self.student's academic records as our sponsor user -> should be allowed (200)
        url_my = reverse('academic_records') + f"?student_id={self.student.id}"
        response_my = self.client.get(url_my)
        self.assertEqual(response_my.status_code, status.HTTP_200_OK)


