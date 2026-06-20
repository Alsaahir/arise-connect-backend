from django.urls import path
from . import views

urlpatterns = [
    path('', views.UserLogin, name="login"),
    path('Arise/get_routes', views.getRoutes, name='get_routes'),
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
]



