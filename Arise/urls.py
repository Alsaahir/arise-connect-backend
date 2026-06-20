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
]

