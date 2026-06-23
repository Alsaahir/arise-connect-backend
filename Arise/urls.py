from django.urls import path
from . import views

urlpatterns = [
    path('', views.UserLogin, name="login"),
    path('Arise/get_routes', views.getRoutes, name='get_routes'),
    path('api/staff/', views.StaffListView.as_view(), name='staff_list'),
    path('api/staff/<uuid:pk>/', views.StaffUpdateView.as_view(), name='staff_update'),
    path('api/staff/complete/', views.UpdateStaffProfileView.as_view(), name='complete_staff_profile'),
    path('api/staff/create/', views.CreateStaffView.as_view(), name='create_staff'),
    path('api/password-reset/request/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/password-reset/verify-otp/', views.PasswordResetVerifyOTPView.as_view(), name='password_reset_verify_otp'),
    path('api/password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('api/contact/', views.ContactSubmitView.as_view(), name='contact_submit'),
    path('api/stories/', views.StoryListCreateView.as_view(), name='story_list_create'),
    path('api/stories/<uuid:pk>/', views.StoryDetailView.as_view(), name='story_detail'),
    path('api/students/', views.StudentListCreateView.as_view(), name='student_list_create'),
    path('api/students/<uuid:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('api/students/<uuid:pk>/sponsor/', views.SponsorStudentView.as_view(), name='sponsor_student'),
    path('api/sponsor/signup/', views.SponsorSignUpView.as_view(), name='sponsor_signup'),
    path('api/sponsor/verify-email/', views.SponsorVerifyEmailView.as_view(), name='sponsor_verify_email'),
    path('api/academic-records/', views.AcademicRecordView.as_view(), name='academic_records'),
    path('api/lesson-plans/', views.LessonPlanView.as_view(), name='lesson_plans'),
    path('api/lesson-plans/<uuid:pk>/', views.LessonPlanDetailView.as_view(), name='lesson_plan_detail'),
    path('api/weekly-reports/', views.WeeklyReportView.as_view(), name='weekly_reports'),
    path('api/notifications/', views.NotificationView.as_view(), name='notifications'),
    path('api/reports/', views.ReportView.as_view(), name='reports'),
    path('api/reports/<uuid:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('api/reports/<uuid:pk>/comments/', views.ReportCommentView.as_view(), name='report_comment'),
]



