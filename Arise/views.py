from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.exceptions import ObjectDoesNotExist
from .models import Staff, PasswordResetOTP, Story, Student, Community, Sponsor, SponsorSignUpOTP, AcademicRecord, LessonPlan, WeeklyReport, Notification, Report, ReportComment, Sponsorship
from .serializers import StorySerializer, StudentSerializer, LessonPlanSerializer, WeeklyReportSerializer, NotificationSerializer, ReportSerializer, ReportCommentSerializer



import string
import random
import datetime
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from rest_framework_simplejwt.tokens import RefreshToken


def UserLogin(request):
    if request.method == 'POST':
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
    
        user = authenticate(request, email=email, password=password)
 
        if user is not None:
            login(request, user)
            return redirect('get_routes')
    return render(request, 'index.html')


# VIEW TO HANDLE USER LOGOUT
class UserLogout(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_200_OK)



@api_view(['GET'])
def getRoutes(request):
    routes = [
        {'POST': 'api/login/'},
        {'POST': 'api/logout/'},
        {'POST': 'api/register/'},
        {'GET': 'api/user/'},
        {'POST': 'api/talent_signup/'},
        {'POST': 'api/company_signup/'},
        {'GET': 'api/create_project/'},
        {'POST': 'api/create_issue/'},
        {'POST': 'api/create_comment/'},
        {'GET': 'api/create_team/'},

        {'POST': 'api/token/'},
        {'POST': 'api/token/refresh/'},
        {'POST': 'api/token/verify/'},
        {'PATCH': 'api/staff/complete/'},
        {'POST': 'api/staff/create/'},
        {'GET/POST': 'api/stories/'},
        {'GET/PUT/DELETE': 'api/stories/<uuid:pk>/'},
        {'GET/POST': 'api/students/'},
        {'GET/PUT/DELETE': 'api/students/<uuid:pk>/'},
    ]
    return Response(routes)

User = get_user_model()


class StaffListView(APIView):
    """GET /api/staff/?role=CSO — list staff members (excluding self), optionally filtered by account_type."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.query_params.get('role', '').strip()
        try:
            current_staff = request.user.staff
            current_staff_id = current_staff.id
        except ObjectDoesNotExist:
            current_staff_id = None

        qs = Staff.objects.all()
        if current_staff_id:
            qs = qs.exclude(id=current_staff_id)
        if role:
            qs = qs.filter(account_type__iexact=role)

        data = []
        for s in qs:
            profile_image_url = None
            if s.profile_image:
                try:
                    url = str(s.profile_image)
                    if url.startswith('http'):
                        profile_image_url = url
                    else:
                        profile_image_url = request.build_absolute_uri(s.profile_image.url)
                except Exception:
                    profile_image_url = None

            data.append({
                "id": str(s.id),
                "full_name": s.full_name,
                "email": s.email,
                "account_type": s.account_type,
                "job_title": s.job_title,
                "station": s.station,
                "community": str(s.community) if s.community else None,
                "is_active": s.is_active,
                "profile_image": profile_image_url,
            })
        return Response(data, status=status.HTTP_200_OK)


class StaffUpdateView(APIView):
    """PATCH /api/staff/<id>/ — update another staff member's account_type.
    Only CSD and EduAdmin can do this. They cannot assign the 'american' role."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            requester_staff = request.user.staff
            requester_role = (requester_staff.account_type or '').lower()
        except ObjectDoesNotExist:
            return Response({"detail": "Requester staff profile not found."}, status=status.HTTP_403_FORBIDDEN)

        allowed_roles = ('csd', 'eduadmin', 'edu-admin', 'education admin')
        if not any(r in requester_role for r in allowed_roles):
            return Response({"detail": "You do not have permission to update staff roles."}, status=status.HTTP_403_FORBIDDEN)

        try:
            target_staff = Staff.objects.get(id=pk)
        except Staff.DoesNotExist:
            return Response({"detail": "Staff member not found."}, status=status.HTTP_404_NOT_FOUND)

        # Prevent assigning self
        if target_staff.id == requester_staff.id:
            return Response({"detail": "You cannot update your own account type here."}, status=status.HTTP_400_BAD_REQUEST)

        new_account_type = request.data.get('account_type', '').strip()
        if not new_account_type:
            return Response({"detail": "account_type is required."}, status=status.HTTP_400_BAD_REQUEST)

        # CSD and EduAdmin cannot assign the 'american' role
        if 'american' in new_account_type.lower():
            return Response({"detail": "You are not allowed to assign the American role."}, status=status.HTTP_403_FORBIDDEN)

        target_staff.account_type = new_account_type
        target_staff.save()

        return Response({
            "id": str(target_staff.id),
            "full_name": target_staff.full_name,
            "account_type": target_staff.account_type,
        }, status=status.HTTP_200_OK)



class UpdateStaffProfileView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        user = request.user
        try:
            staff = user.staff
        except ObjectDoesNotExist:
            return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": str(staff.id),
            "full_name": staff.full_name,
            "email": staff.email,
            "phone_number": staff.phone_number,
            "job_title": staff.job_title,
            "community": str(staff.community) if staff.community else None,
            "station": staff.station,
            "account_type": staff.account_type,
            "address_line_1": staff.address_line_1,
            "address_line_2": staff.address_line_2,
            "country": staff.country,
            "state": staff.state,
            "city": staff.city,
            "zip_code": staff.zip_code,
            "profile_image": staff.profile_image if staff.profile_image else None,
            "is_active": staff.is_active,
            "is_complete": staff.is_complete,
        }, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        try:
            staff = user.staff
        except ObjectDoesNotExist:
            return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Handle user password update if provided
        password = request.data.get('password')
        if password and str(password).strip() != '':
            user.set_password(password)
            user.save()

        # Handle staff profile image update if provided
        profile_image = request.data.get('profile_image') or request.FILES.get('profile_image')
        if profile_image and not isinstance(profile_image, str):
            staff.profile_image = profile_image

        editable_fields = [
            'full_name', 'email', 'phone_number', 'job_title', 'community',
            'station', 'account_type', 'address_line_1', 'address_line_2',
            'country', 'state', 'city', 'zip_code'
        ]

        for field in editable_fields:
            if field in request.data:
                val = request.data[field]
                if field == 'community' and val:
                    from uuid import UUID
                    try:
                        val = UUID(val)
                    except ValueError:
                        import uuid
                        val = uuid.uuid4()
                setattr(staff, field, val)

        staff.save()

        # Only address_line_1 is mandatory for profile completion
        address_1_val = getattr(staff, 'address_line_1', '')
        if address_1_val and str(address_1_val).strip() != '':
            staff.is_complete = True
            staff.save()

        return Response({
            "id": str(staff.id),
            "full_name": staff.full_name,
            "email": staff.email,
            "phone_number": staff.phone_number,
            "job_title": staff.job_title,
            "community": str(staff.community) if staff.community else None,
            "station": staff.station,
            "account_type": staff.account_type,
            "address_line_1": staff.address_line_1,
            "address_line_2": staff.address_line_2,
            "country": staff.country,
            "state": staff.state,
            "city": staff.city,
            "zip_code": staff.zip_code,
            "profile_image": staff.profile_image if staff.profile_image else None,
            "is_complete": staff.is_complete
        }, status=status.HTTP_200_OK)


class CreateStaffView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        role_filter = request.query_params.get('role')
        staff_members = Staff.objects.filter(is_active=True)
        if role_filter:
            staff_members = staff_members.filter(account_type__icontains=role_filter)
        
        data = [{
            "id": str(s.id),
            "full_name": s.full_name,
            "email": s.email,
            "account_type": s.account_type,
            "station": s.station
        } for s in staff_members]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        creator_user = request.user
        
        try:
            creator_staff = creator_user.staff
            creator_role = creator_staff.account_type.lower() if creator_staff.account_type else ""
        except ObjectDoesNotExist:
            creator_role = ""

        is_creator_allowed = (
            creator_user.is_superuser or 
            creator_role in ["eduadmin", "edu-admin", "csd", "american", "american-staff"]
        )
        if not is_creator_allowed:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        full_name = request.data.get('full_name', '')
        email = request.data.get('email', '')
        account_type = request.data.get('account_type', '')
        job_title = request.data.get('job_title', '')
        community_str = request.data.get('community', '')
        station = request.data.get('station', '')
        profile_image = request.FILES.get('profile_image', None)

        if not full_name or not email or not account_type:
            return Response({"detail": "Full Name, Email, and Account Type are required."}, status=status.HTTP_400_BAD_REQUEST)

        normalized_account_type = account_type.lower().strip()

        if creator_role in ["csd", "eduadmin", "edu-admin"] and normalized_account_type in ["american", "american-staff"]:
            return Response({"detail": "CSD and EduAdmin users cannot create American-staff accounts."}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            return Response({"detail": "A user with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        community = None
        if community_str:
            from uuid import UUID
            try:
                community = UUID(community_str)
            except ValueError:
                pass

        temp_password = "Arise@" + "".join(random.choices(string.digits, k=8))
        
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        new_user = User.objects.create_user(
            email=email,
            password=temp_password,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_staff=True,
            is_superuser=False
        )

        staff = Staff.objects.create(
            user=new_user,
            full_name=full_name,
            email=email,
            job_title=job_title,
            community=community,
            station=station,
            account_type=account_type,
            profile_image=profile_image,
            is_complete=False
        )

        subject = "Welcome to Arise Connect - Complete Your Profile"
        message = f"""Hello {full_name},

Your staff account has been created on Arise Connect.

Account Details:
- Role: {account_type}
- Job Title: {job_title}

Please log in using the following temporary credentials:
Email: {email}
Temporary Password: {temp_password}

Click the link below to log in and complete your profile:
http://localhost:5173/

Best regards,
Arise Connect Team"""

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL or 'noreply@ariseconnect.org',
                [email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send email to {email}: {e}")

        return Response({
            "id": str(staff.id),
            "full_name": staff.full_name,
            "email": staff.email,
            "account_type": staff.account_type,
            "job_title": staff.job_title,
            "community": str(staff.community) if staff.community else None,
            "station": staff.station,
            "profile_image": staff.profile_image if staff.profile_image else None,
            "is_complete": staff.is_complete
        }, status=status.HTTP_201_CREATED)


class PasswordResetRequestView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        from .models import PasswordResetOTP
        
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"detail": "No user account found with this email address."}, status=status.HTTP_404_NOT_FOUND)
        
        import random
        otp = "".join(random.choices("0123456789", k=5))
        
        email=user.email

        PasswordResetOTP.objects.update_or_create(
            email=email,
            defaults={'otp': otp}
        )
        
        subject = "Your Password Reset OTP - Arise Connect"
        message = f"""Hello {user.first_name or ''},

We received a request to reset your password on Arise Connect.

Your 5-digit One-Time Password (OTP) is: {otp}

This OTP is valid for 10 minutes.

If you did not request this, you can ignore this email.

Best regards,
Arise Connect Team"""
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL or 'jacobdjango7@gmail.com',
                [email],
                fail_silently=False,
            )
            print(f"{otp}")
        except Exception as e:
            print(f"Failed to send password reset OTP: {e}")
            if settings.DEBUG:
                print(f"\n========================================\n[DEBUG] PASSWORD RESET OTP FOR {user.email}: {otp}\n========================================\n")
                return Response({
                    "detail": "A 5-digit OTP has been generated (sent to console due to email configuration error)."
                }, status=status.HTTP_200_OK)
            return Response({"detail": "Error sending email. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response({"detail": "A 5-digit OTP has been sent to your email."}, status=status.HTTP_200_OK)


class PasswordResetVerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip()
        otp = request.data.get('otp', '')
        
        if not email or not otp:
            return Response({"detail": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.utils import timezone
        from datetime import timedelta
        from .models import PasswordResetOTP
        
        try:
            otp_record = PasswordResetOTP.objects.get(email__iexact=email)
        except PasswordResetOTP.DoesNotExist:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
            
        if timezone.now() > otp_record.created_at + timedelta(minutes=10):
            otp_record.delete()
            return Response({"detail": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
            
        if otp_record.otp != otp:
            return Response({"detail": "Incorrect OTP."}, status=status.HTTP_400_BAD_REQUEST)
            
        otp_record.delete()
        
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        return Response({
            "detail": "OTP verified successfully.",
            "uidb64": uidb64,
            "token": token
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    def post(self, request):
        uidb64 = request.data.get('uidb64', '')
        token = request.data.get('token', '')
        password = request.data.get('password', '')
        
        if not uidb64 or not token or not password:
            return Response({"detail": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)
        
        User = get_user_model()
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired reset token."}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.save()
        
        # Log the user in and return JWT tokens and staff details
        refresh = RefreshToken.for_user(user)
        
        staff_data = None
        try:
            staff = user.staff
            staff_data = {
                "id": str(staff.id),
                "full_name": staff.full_name,
                "email": staff.email,
                "phone_number": staff.phone_number,
                "job_title": staff.job_title,
                "community": str(staff.community) if staff.community else None,
                "station": staff.station,
                "account_type": staff.account_type,
                "address_line_1": staff.address_line_1,
                "address_line_2": staff.address_line_2,
                "country": staff.country,
                "state": staff.state,
                "city": staff.city,
                "zip_code": staff.zip_code,
                "profile_image": staff.profile_image if staff.profile_image else None,
                "is_active": staff.is_active,
                "is_complete": staff.is_complete,
            }
        except ObjectDoesNotExist:
            staff = Staff.objects.create(
                user=user,
                email=user.email,
                full_name=f"{user.first_name} {user.last_name}".strip() if (user.first_name or user.last_name) else user.email,
                account_type="Sponsor"
            )
            staff_data = {
                "id": str(staff.id),
                "full_name": staff.full_name,
                "email": staff.email,
                "account_type": staff.account_type,
                "profile_image": None,
                "is_complete": staff.is_complete,
            }
        
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "staff": staff_data
        }, status=status.HTTP_200_OK)


class ContactSubmitView(APIView):
    def post(self, request):
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip()
        subject = request.data.get('subject', '').strip()
        message = request.data.get('message', '').strip()
        
        if not name or not email or not subject or not message:
            return Response({"detail": "All fields (name, email, subject, message) are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        email_subject = f"[Contact Form] {subject}"
        email_message = f"""You received a new message from the contact form:

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}
"""
        from django.core.mail import EmailMessage
        try:
            email_msg = EmailMessage(
                subject=email_subject,
                body=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@ariseconnect.org',
                to=[settings.DEFAULT_FROM_EMAIL or 'jacobdjango7@gmail.com'],
                reply_to=[email],
            )
            email_msg.send(fail_silently=False)
        except Exception as e:
            print(f"Failed to send contact email: {e}")
            return Response({"detail": "Failed to send email. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response({"detail": "Thank you for your message! We will get back to you soon."}, status=status.HTTP_200_OK)


class StoryListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        stories = Story.objects.all().order_by('-created_at')
        serializer = StorySerializer(stories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = StorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StoryDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, pk):
        try:
            return Story.objects.get(pk=pk)
        except Story.DoesNotExist:
            return None

    def get(self, request, pk):
        story = self.get_object(pk)
        if not story:
            return Response({"detail": "Story not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = StorySerializer(story)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        story = self.get_object(pk)
        if not story:
            return Response({"detail": "Story not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = StorySerializer(story, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        story = self.get_object(pk)
        if not story:
            return Response({"detail": "Story not found."}, status=status.HTTP_404_NOT_FOUND)
        story.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudentListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        students = Student.objects.all().order_by('-created_at')
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = request.data.copy()

        if 'Student_number' not in data or not data['Student_number']:
            import random
            while True:
                num = random.randint(100000, 999999)
                if not Student.objects.filter(Student_number=num).exists():
                    data['Student_number'] = num
                    break

        school_name = request.data.get('school', '')
        cso_name = request.data.get('cso', '')

        if school_name:
            community, _ = Community.objects.get_or_create(Name=school_name)
            data['Community_id'] = str(community.id)

        if cso_name:
            staff = Staff.objects.filter(full_name__iexact=cso_name).first()
            if not staff:
                User = get_user_model()
                username = cso_name.lower().replace(' ', '.')
                user_email = f"{username}@example.com"
                user = User.objects.filter(email=user_email).first()
                if not user:
                    user = User.objects.create_user(
                        email=user_email,
                        password='Password123',
                        first_name=cso_name.split()[0] if cso_name.split() else cso_name,
                        last_name=cso_name.split()[1] if len(cso_name.split()) > 1 else '',
                        is_active=True,
                        is_staff=True,
                        is_superuser=False
                    )
                staff = Staff.objects.create(
                    user=user,
                    full_name=cso_name,
                    email=user_email,
                    account_type='CSO',
                    is_active=True
                )
            data['CSO_id'] = str(staff.id)
        else:
            data['CSO_id'] = None

        serializer = StudentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentDetailView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        try:
            return Student.objects.get(pk=pk)
        except Student.DoesNotExist:
            return None

    def get(self, request, pk):
        student = self.get_object(pk)
        if not student:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = StudentSerializer(student)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        student = self.get_object(pk)
        if not student:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Parse data safely
        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = request.data.copy()

        import json
        
        # Handle parsed json if passed as fields
        demographics_data = data.pop('demographics', None)
        guardian_data = data.pop('guardian', None)
        health_conditions_data = data.pop('healthConditions', None)

        # Handle Student fields mapping
        if 'gender' in data:
            data['Gender'] = data.pop('gender')
        if 'birthday' in data:
            data['Date_of_birth'] = data.pop('birthday')
        if 'grade' in data:
            data['Current_grade'] = data.pop('grade')
        if 'enrollmentTerm' in data:
            data['Enrollment_term'] = data.pop('enrollmentTerm')
        if 'enrollmentYear' in data:
            data['Enrollment_year'] = data.pop('enrollmentYear')
        
        school_name = data.pop('school', None)
        if school_name:
            community, _ = Community.objects.get_or_create(Name=school_name)
            data['Community_id'] = str(community.id)
        
        cso_name = data.pop('cso', None)
        if cso_name is not None:
            if not cso_name or cso_name.lower() in ['none', 'blank', 'none / blank']:
                data['CSO_id'] = None
            else:
                staff = Staff.objects.filter(full_name__iexact=cso_name).first()
                if not staff:
                    User = get_user_model()
                    username = cso_name.lower().replace(' ', '.')
                    user_email = f"{username}@example.com"
                    user = User.objects.filter(email=user_email).first()
                    if not user:
                        user = User.objects.create_user(
                            email=user_email,
                            password='Password123',
                            first_name=cso_name.split()[0] if cso_name.split() else cso_name,
                            last_name=cso_name.split()[1] if len(cso_name.split()) > 1 else '',
                            is_active=True,
                            is_staff=True,
                            is_superuser=False
                        )
                    staff = Staff.objects.create(
                        user=user,
                        full_name=cso_name,
                        email=user_email,
                        account_type='CSO',
                        is_active=True
                    )
                data['CSO_id'] = str(staff.id)

        serializer = StudentSerializer(student, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            def to_int(val, default=None):
                if val == '' or val is None:
                    return default
                try:
                    return int(val)
                except ValueError:
                    return default
            
            def to_bool(val):
                if val == 'yes' or val is True:
                    return True
                if val == 'no' or val is False:
                    return False
                return False

            if demographics_data:
                if isinstance(demographics_data, str):
                    try:
                        demographics_data = json.loads(demographics_data)
                    except Exception:
                        pass
                if isinstance(demographics_data, dict):
                    demog, _ = DemographicHealthDetails.objects.get_or_create(Student=student)
                    demog.Living_parents = demographics_data.get('parents', demog.Living_parents)
                    demog.Mother_relationship = demographics_data.get('motherRel', demog.Mother_relationship)
                    demog.Father_relationship = demographics_data.get('fatherRel', demog.Father_relationship)
                    demog.Siblings = to_int(demographics_data.get('numSiblings'), demog.Siblings)
                    demog.Distance_to_school = to_int(demographics_data.get('walkToSchool'), demog.Distance_to_school)
                    demog.Meals_per_week = to_int(demographics_data.get('fullMeals'), demog.Meals_per_week)
                    demog.People_in_the_house = to_int(demographics_data.get('householdPeople'), demog.People_in_the_house)
                    demog.People_in_school = to_int(demographics_data.get('householdInSchool'), demog.People_in_school)
                    demog.Reliable_income = to_int(demographics_data.get('reliableIncome'), demog.Reliable_income)
                    demog.can_read = to_int(demographics_data.get('householdCanRead'), demog.can_read)
                    demog.Distance_to_water = to_int(demographics_data.get('waterDistance'), demog.Distance_to_water)
                    demog.Has_electricity = to_bool(demographics_data.get('hasElectricity'))
                    demog.Has_water = to_bool(demographics_data.get('hasRunningWater'))
                    demog.HIV_status = to_bool(demographics_data.get('hivPositive'))
                    demog.Has_disability = to_bool(demographics_data.get('hasDisability'))
                    demog.Demographic_comments = demographics_data.get('comments', demog.Demographic_comments)
                    demog.save()

            if guardian_data:
                if isinstance(guardian_data, str):
                    try:
                        guardian_data = json.loads(guardian_data)
                    except Exception:
                        pass
                if isinstance(guardian_data, dict):
                    guard, _ = GuardianInformation.objects.get_or_create(student=student)
                    guard.Guardian_name = guardian_data.get('name', guard.Guardian_name)
                    guard.Guardian_phone_number = guardian_data.get('phone', guard.Guardian_phone_number)
                    guard.Guardian_NRC = guardian_data.get('nrc', guard.Guardian_NRC)
                    guard.Caretaker_occupation = guardian_data.get('occupation', guard.Caretaker_occupation)
                    
                    caretakers = guardian_data.get('primaryCaretaker', [])
                    if isinstance(caretakers, list):
                        guard.Primary_caretaker = ", ".join(caretakers)
                    else:
                        guard.Primary_caretaker = caretakers
                    
                    guard.Highest_education = guardian_data.get('education', guard.Highest_education)
                    guard.Can_read = to_bool(guardian_data.get('canRead'))
                    guard.Guardian_comments = guardian_data.get('notes', guard.Guardian_comments)
                    guard.save()

            if health_conditions_data is not None:
                if isinstance(health_conditions_data, str):
                    try:
                        health_conditions_data = json.loads(health_conditions_data)
                    except Exception:
                        pass
                if isinstance(health_conditions_data, list):
                    HealthConditions.objects.filter(Student=student).delete()
                    for condition_name in health_conditions_data:
                        if condition_name:
                            HealthConditions.objects.create(
                                Student=student,
                                Condition_name=condition_name,
                                Condition_status='Active'
                            )

            response_serializer = StudentSerializer(student)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        student = self.get_object(pk)
        if not student:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        student.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SponsorSignUpView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        full_name = request.data.get('full_name', '').strip()
        email = request.data.get('email', '').strip()
        phone_number = request.data.get('phone_number', '').strip()
        address_line_1 = request.data.get('address_line_1', '').strip()
        address_line_2 = request.data.get('address_line_2', '').strip()
        country = request.data.get('country', '').strip()
        state = request.data.get('state', '').strip()
        city = request.data.get('city', '').strip()
        zip_code = request.data.get('zip_code', '').strip()
        password = request.data.get('password', '')
        profile_photo = request.FILES.get('profile_photo', None)

        if not full_name or not email or not address_line_1 or not password:
            return Response({"detail": "Full Name, Email, Address Line 1, and Password are required."}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            return Response({"detail": "A user account with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a 5-digit verification OTP
        import random
        otp = "".join(random.choices("0123456789", k=5))

        from django.db import transaction

        try:
            with transaction.atomic():
                # Create the inactive user
                name_parts = full_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                new_user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False, # inactive until email is verified via OTP
                    is_staff=False,
                    is_superuser=False
                )

                # Create the inactive staff mapped record (since custom SimpleJWT validate maps to user.staff, we must have one)
                staff = Staff.objects.create(
                    user=new_user,
                    full_name=full_name,
                    email=email,
                    phone_number=phone_number,
                    account_type='Sponsor',
                    address_line_1=address_line_1,
                    address_line_2=address_line_2,
                    country=country,
                    state=state,
                    city=city,
                    zip_code=zip_code,
                    is_active=False,
                    is_complete=True
                )

                # Create the Sponsor model record
                import random
                sponsor_number = f"SP{random.randint(100000, 999999)}"
                while Sponsor.objects.filter(Sponsor_number=sponsor_number).exists():
                    sponsor_number = f"SP{random.randint(100000, 999999)}"

                sponsor = Sponsor.objects.create(
                    User=new_user,
                    staff=staff,
                    Full_name=full_name,
                    Email=email,
                    Phone_number=phone_number,
                    Sponsor_number=sponsor_number,
                    Address_line_1=address_line_1,
                    Address_line_2=address_line_2,
                    Country=country,
                    State=state,
                    City=city,
                    Zip_code=zip_code,
                    profile_photo=profile_photo
                )

                # Store signup OTP
                SponsorSignUpOTP.objects.update_or_create(
                    email=email,
                    defaults={'otp': otp}
                )

                # Send OTP email
                subject = "Verify Your Email - Arise Connect Sponsor Registration"
                message = f"""Hello {first_name},
                
Thank you for registering as a Sponsor on Arise Connect.

Your 5-digit One-Time Password (OTP) to verify your email is: {otp}

This OTP is valid for 10 minutes.

Best regards,
Arise Connect Team"""

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL or 'noreply@ariseconnect.org',
                        [email],
                        fail_silently=False,
                    )
                    print(f"SignUp OTP: {otp}")
                except Exception as e:
                    print(f"Failed to send sponsor verification OTP email: {e}")
                    if settings.DEBUG:
                        print(f"\n========================================\n[DEBUG] SPONSOR SIGNUP OTP FOR {email}: {otp}\n========================================\n")
                    else:
                        raise e
        except Exception as e:
            # Transaction has been rolled back automatically
            return Response({"detail": "Error sending verification email or creating account. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"detail": "A verification OTP has been sent to your email."}, status=status.HTTP_201_CREATED)


class SponsorVerifyEmailView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip()
        otp = request.data.get('otp', '')

        if not email or not otp:
            return Response({"detail": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        from datetime import timedelta

        try:
            otp_record = SponsorSignUpOTP.objects.get(email__iexact=email)
        except SponsorSignUpOTP.DoesNotExist:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > otp_record.created_at + timedelta(minutes=10):
            otp_record.delete()
            return Response({"detail": "OTP has expired. Please register again."}, status=status.HTTP_400_BAD_REQUEST)

        if otp_record.otp != otp:
            return Response({"detail": "Incorrect OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # OTP is correct, activate the user and their staff record
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email)
            user.is_active = True
            user.save()

            if hasattr(user, 'staff'):
                user.staff.is_active = True
                user.staff.save()
        except User.DoesNotExist:
            return Response({"detail": "Associated user account not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Cleanup OTP
        otp_record.delete()

        return Response({"detail": "Email verified and account activated successfully."}, status=status.HTTP_200_OK)


class AcademicRecordView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student_id = request.query_params.get('student_id')
        if student_id:
            try:
                student = Student.objects.get(pk=student_id)
            except Student.DoesNotExist:
                return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                sponsor = Sponsor.objects.get(User=request.user)
                if student.Sponsor_id != sponsor:
                    return Response({"detail": "You are not authorized to view this student's academic records."}, status=status.HTTP_403_FORBIDDEN)
            except Sponsor.DoesNotExist:
                pass

            records = AcademicRecord.objects.filter(student=student).order_by('-year')
            # Group records by year and grade
            from collections import defaultdict
            grouped = defaultdict(list)
            for r in records:
                grouped[(r.year, r.grade)].append(r)
            
            history = []
            for (year, grade), recs in grouped.items():
                subjects_data = {}
                for r in recs:
                    subjects_data[r.subject] = [r.mt1, r.et1, r.mt2, r.et2, r.mt3, r.et3]
                
                # Calculate averages for status/strengths/weaknesses
                all_scores = []
                for sub, scores in subjects_data.items():
                    valid = [s for s in scores if s is not None]
                    if valid:
                        all_scores.extend(valid)
                
                avg = sum(all_scores) / len(all_scores) if all_scores else None
                
                # Determine strengths / weaknesses
                strengths = []
                weaknesses = []
                for sub, scores in subjects_data.items():
                    valid = [s for s in scores if s is not None]
                    if valid:
                        sub_avg = sum(valid) / len(valid)
                        if sub_avg >= 75:
                            strengths.append(sub)
                        elif sub_avg < 60:
                            weaknesses.append(sub)
                
                if not strengths:
                    # Fallback if no sub >= 75
                    sorted_subs = sorted(
                        subjects_data.keys(),
                        key=lambda s: sum([v for v in subjects_data[s] if v is not None]) / len([v for v in subjects_data[s] if v is not None]) if [v for v in subjects_data[s] if v is not None] else 0,
                        reverse=True
                    )
                    if sorted_subs:
                        strengths = sorted_subs[:1]
                
                if avg is not None:
                    if avg >= 80:
                        status_str = "Excellent"
                        comment = f"{student.Full_name} has shown outstanding performance this academic year, particularly in {', '.join(strengths) if strengths else 'all subjects'}."
                    elif avg >= 65:
                        status_str = "Good"
                        comment = f"{student.Full_name} is performing well and making steady progress. Keep up the good work!"
                    else:
                        status_str = "Needs Improvement"
                        comment = f"{student.Full_name} needs some additional support and guidance, especially in {', '.join(weaknesses) if weaknesses else 'core subjects'}."
                else:
                    status_str = "Good"
                    comment = f"No score data recorded for {student.Full_name} yet."
                
                history.append({
                    "year": year,
                    "grade": grade,
                    "status": status_str,
                    "overallAvg": round(avg, 1) if avg is not None else "N/A",
                    "strengths": strengths if strengths else ["None"],
                    "weaknesses": weaknesses if weaknesses else ["None"],
                    "teacherComment": comment,
                    "subjects": subjects_data
                })
            
            return Response({
                "student_id": str(student.id),
                "name": student.Full_name,
                "history": history
            }, status=status.HTTP_200_OK)

        year_str = request.query_params.get('year')
        grade = request.query_params.get('grade')
        
        if not year_str or not grade:
            return Response({"detail": "Year and Grade are required parameters."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year = int(year_str)
        except ValueError:
            return Response({"detail": "Invalid year format."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse grade number
        import re
        grade_num = None
        match = re.search(r'\d+', grade)
        if match:
            grade_num = int(match.group())
        elif "kinder" in grade.lower():
            grade_num = 0
        
        if grade_num is None:
            return Response({"detail": "Invalid grade format."}, status=status.HTTP_400_BAD_REQUEST)

        # Find all students who are in this grade (current_grade), OR who have existing academic records for this year and grade
        from django.db.models import Q
        students = Student.objects.filter(
            Q(Current_grade=grade_num) | Q(academic_records__year=year, academic_records__grade=grade)
        ).distinct()

        # Define default subjects for each grade
        GRADE_SUBJECTS = {
            'Pre-Kinder': ['Shapes', 'Colors', 'Letters', 'Basic Phonics'],
            'Kinder': ['Literacy', 'Numeracy', 'Phonics', 'Arts & Craft'],
            'Grade 1': ['English', 'Mathematics', 'Environmental Science', 'Local Language (Lozi)', 'Life Skills'],
            'Grade 2': ['English', 'Mathematics', 'Social Studies', 'Local Language (Bemba)', 'Health Education'],
            'Grade 3': ['English', 'Mathematics', 'Science', 'Social Studies', 'ICT', 'Religious Ed.'],
            'Grade 4': ['English', 'Mathematics', 'Science', 'Social Studies', 'Art', 'Zambian Studies'],
            'Grade 5': ['English', 'Mathematics', 'Science', 'Social Studies', 'Home Economics', 'P.E.'],
            'Grade 6': ['English', 'Mathematics', 'Science', 'Social Studies', 'Music', 'ICT'],
            'Grade 7': ['Mathematics', 'English Language', 'Integrated Science', 'Geography'],
            'Grade 8': ['Mathematics', 'English Language', 'Physics', 'Chemistry', 'Biology', 'Civics', 'Business Studies'],
            'Grade 9': ['Mathematics', 'English Language', 'Physics', 'Chemistry', 'Biology', 'Computer Studies', 'Agricultural Science'],
            'Grade 10': ['Mathematics (Core)', 'English Language', 'Commerce', 'Accounting', 'French', 'Physical Science', 'Humanities'],
            'Grade 11': ['Mathematics (Core)', 'English Language', 'Physics', 'Chemistry', 'Biology', 'Design & Tech', 'Geography'],
            'Grade 12': ['Mathematics (Core)', 'English Language', 'Literature', 'Economics', 'Business Studies', 'ICT', 'Art & Design'],
        }
        
        # Get standard subjects list
        default_subjects = GRADE_SUBJECTS.get(grade, [])

        student_list = []
        for s in students:
            # Get existing records for this student, year, and grade
            records = AcademicRecord.objects.filter(student=s, year=year, grade=grade)
            
            # Map existing records by subject name
            record_map = {r.subject: r for r in records}
            
            # Build subjects dict
            subjects_data = {}
            
            # 1. Process default subjects
            for sub in default_subjects:
                if sub in record_map:
                    r = record_map[sub]
                    subjects_data[sub] = [r.mt1, r.et1, r.mt2, r.et2, r.mt3, r.et3]
                else:
                    subjects_data[sub] = [None, None, None, None, None, None]
            
            # 2. Add other subjects that might be stored in the database but aren't in default list
            for sub, r in record_map.items():
                if sub not in subjects_data:
                    subjects_data[sub] = [r.mt1, r.et1, r.mt2, r.et2, r.mt3, r.et3]

            student_list.append({
                "id": str(s.id),
                "name": s.Full_name,
                "subjects": subjects_data
            })

        return Response({
            "year": year,
            "grade": grade,
            "students": student_list
        }, status=status.HTTP_200_OK)

    def post(self, request):
        year_str = request.data.get('year')
        grade = request.data.get('grade')
        students_data = request.data.get('students', [])

        if not year_str or not grade:
            return Response({"detail": "Year and Grade are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            year = int(year_str)
        except ValueError:
            return Response({"detail": "Invalid year format."}, status=status.HTTP_400_BAD_REQUEST)

        # We will save or update AcademicRecord objects in bulk
        from django.db import transaction
        try:
            with transaction.atomic():
                for s_data in students_data:
                    student_id = s_data.get('id')
                    subjects = s_data.get('subjects', {})

                    try:
                        student = Student.objects.get(pk=student_id)
                    except Student.DoesNotExist:
                        continue  # Skip if student doesn't exist

                    for subject_name, scores in subjects.items():
                        if not isinstance(scores, list) or len(scores) < 6:
                            continue
                        
                        def clean_score(val):
                            if val is None or val == '' or str(val).lower() == 'n/a':
                                return None
                            try:
                                return int(val)
                            except ValueError:
                                return None

                        AcademicRecord.objects.update_or_create(
                            student=student,
                            year=year,
                            grade=grade,
                            subject=subject_name,
                            defaults={
                                'mt1': clean_score(scores[0]),
                                'et1': clean_score(scores[1]),
                                'mt2': clean_score(scores[2]),
                                'et2': clean_score(scores[3]),
                                'mt3': clean_score(scores[4]),
                                'et3': clean_score(scores[5]),
                            }
                        )
            return Response({"detail": "Academic records updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            print("Error updating academic records:", e)
            return Response({"detail": "Error saving records to database. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LessonPlanView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        staff = request.user.staff
        role = staff.account_type.lower()
        if role == 'eduadmin':
            plans = LessonPlan.objects.all().order_by('-created_at')
        else:
            plans = LessonPlan.objects.filter(teacher=staff).order_by('-created_at')
        
        serializer = LessonPlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        staff = request.user.staff
        data = request.data.copy()
        data['teacher'] = str(staff.id)
        
        serializer = LessonPlanSerializer(data=data)
        if serializer.is_valid():
            lesson_plan = serializer.save()
            
            if lesson_plan.status.lower() == 'pending':
                eduadmins = Staff.objects.filter(account_type__iexact='eduadmin')
                for admin in eduadmins:
                    Notification.objects.create(
                        recipient=admin,
                        title="New Lesson Plan Submitted",
                        message=f"Teacher {staff.full_name} has submitted a new lesson plan: '{lesson_plan.title}' for approval."
                    )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LessonPlanDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return LessonPlan.objects.get(pk=pk)
        except LessonPlan.DoesNotExist:
            return None

    def get(self, request, pk):
        plan = self.get_object(pk)
        if not plan:
            return Response({"detail": "Lesson plan not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = LessonPlanSerializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        plan = self.get_object(pk)
        if not plan:
            return Response({"detail": "Lesson plan not found."}, status=status.HTTP_404_NOT_FOUND)
        
        staff = request.user.staff
        role = staff.account_type.lower()
        
        old_status = plan.status.lower()
        new_status = request.data.get('status', '').lower()
        
        if role == 'eduadmin':
            plan.status = request.data.get('status', plan.status)
            plan.headmaster_comment = request.data.get('headmaster_comment', plan.headmaster_comment)
            plan.save()
            
            if new_status in ['approved', 'rejected'] and old_status != new_status:
                Notification.objects.create(
                    recipient=plan.teacher,
                    title=f"Lesson Plan {new_status.capitalize()}",
                    message=f"Your lesson plan '{plan.title}' has been {new_status} by the Headmaster."
                )
            
            serializer = LessonPlanSerializer(plan)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        elif plan.teacher == staff:
            serializer = LessonPlanSerializer(plan, data=request.data, partial=True)
            if serializer.is_valid():
                updated_plan = serializer.save()
                if new_status == 'pending' and old_status != 'pending':
                    eduadmins = Staff.objects.filter(account_type__iexact='eduadmin')
                    for admin in eduadmins:
                        Notification.objects.create(
                            recipient=admin,
                            title="New Lesson Plan Submitted",
                            message=f"Teacher {staff.full_name} has submitted lesson plan: '{updated_plan.title}' for approval."
                        )
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        else:
            return Response({"detail": "You do not have permission to update this lesson plan."}, status=status.HTTP_403_FORBIDDEN)


class WeeklyReportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        staff = request.user.staff
        role = staff.account_type.lower()
        
        if role == 'teacher':
            reports = WeeklyReport.objects.filter(teacher=staff).order_by('-week_ending_date')
        else:
            reports = WeeklyReport.objects.all().order_by('-week_ending_date')
            
        serializer = WeeklyReportSerializer(reports, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        staff = request.user.staff
        role = staff.account_type.lower()
        
        if role != 'teacher':
            return Response({"detail": "Only teachers can submit weekly reports."}, status=status.HTTP_403_FORBIDDEN)
            
        week_ending_str = request.data.get('week_ending_date')
        if not week_ending_str:
            return Response({"detail": "Week ending date is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        import datetime
        from django.utils import timezone
        
        try:
            week_ending_date = datetime.datetime.strptime(week_ending_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            
        lock_datetime = datetime.datetime.combine(week_ending_date, datetime.time(15, 0))
        default_tz = timezone.get_current_timezone()
        lock_datetime = timezone.make_aware(lock_datetime, default_tz)
        
        if timezone.now() > lock_datetime:
            return Response({"detail": "Weekly reports are locked after Friday 3:00 PM of the report's week."}, status=status.HTTP_400_BAD_REQUEST)
            
        report, created = WeeklyReport.objects.update_or_create(
            teacher=staff,
            week_ending_date=week_ending_date,
            defaults={
                'social_events': request.data.get('social_events', ''),
                'behavioral_issues': request.data.get('behavioral_issues', ''),
                'health_issues': request.data.get('health_issues', ''),
                'absenteeism': request.data.get('absenteeism', ''),
                'other_notes': request.data.get('other_notes', ''),
            }
        )
        
        if created:
            managers = Staff.objects.filter(account_type__iexact='csd') | Staff.objects.filter(account_type__iexact='american') | Staff.objects.filter(account_type__iexact='eduadmin')
            for manager in managers.distinct():
                Notification.objects.create(
                    recipient=manager,
                    title="Weekly Report Submitted",
                    message=f"Teacher {staff.full_name} has submitted the weekly report for week ending {week_ending_date}."
                )

        serializer = WeeklyReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        staff = request.user.staff
        notifications = Notification.objects.filter(recipient=staff).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        staff = request.user.staff
        Notification.objects.filter(recipient=staff).update(is_read=True)
        return Response({"detail": "All notifications marked as read."}, status=status.HTTP_200_OK)


def send_report_email(recipient_email, subject, message):
    if not recipient_email:
        return
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=True
        )
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")


class ReportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        staff = None
        sponsor = None
        try:
            staff = request.user.staff
        except ObjectDoesNotExist:
            try:
                sponsor = Sponsor.objects.filter(User=request.user).first()
            except Exception:
                pass

        if staff:
            role = (staff.account_type or '').lower()
            if 'cso' in role:
                reports = Report.objects.filter(Student__CSO_id=staff).order_by('-Created_at')
            elif 'csd' in role:
                # Auto-assign unassigned communities to this CSD
                unassigned = Community.objects.filter(CSD__isnull=True)
                if unassigned.exists():
                    for comm in unassigned:
                        comm.CSD = staff
                        comm.save()
                # Backfill CSD on any reports that are missing it for this staff's communities
                Report.objects.filter(
                    Student__Community_id__CSD=staff,
                    CSD__isnull=True
                ).update(CSD=staff)
                reports = Report.objects.filter(Student__Community_id__CSD=staff).order_by('-Created_at')
            elif 'american' in role or 'admin' in role:
                reports = Report.objects.all().order_by('-Created_at')
            else:
                reports = Report.objects.filter(Student__Community_id__Headmaster=staff).order_by('-Created_at')
        elif sponsor:
            reports = Report.objects.filter(Student__Sponsor_id=sponsor, status__iexact='Approved').order_by('-Created_at')
        else:
            return Response({"detail": "User profile not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Filters
        status_filter = request.query_params.get('status')
        if status_filter:
            reports = reports.filter(status__iexact=status_filter)

        community_filter = request.query_params.get('community_id')
        if community_filter:
            reports = reports.filter(Student__Community_id_id=community_filter)

        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            staff = request.user.staff
        except ObjectDoesNotExist:
            return Response({"detail": "Only staff members can generate reports."}, status=status.HTTP_403_FORBIDDEN)

        role = (staff.account_type or '').lower()
        if 'csd' not in role and 'admin' not in role and 'american' not in role:
            return Response({"detail": "Only CSDs or administrators can generate reports."}, status=status.HTTP_403_FORBIDDEN)

        community_id = request.data.get('community_id')
        term = request.data.get('term')
        year = request.data.get('year')

        if not community_id or not term or not year:
            return Response({"detail": "community_id, term, and year are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            community = Community.objects.get(pk=community_id)
        except Community.DoesNotExist:
            return Response({"detail": "Community not found."}, status=status.HTTP_404_NOT_FOUND)

        if not community.CSD:
            community.CSD = staff
            community.save()

        # Update existing reports CSD and CSO to ensure they are assigned
        Report.objects.filter(Student__Community_id=community, Report_term=term, CSD__isnull=True).update(CSD=staff)
        for r in Report.objects.filter(Student__Community_id=community, Report_term=term):
            if not r.CSO and r.Student.CSO_id:
                r.CSO = r.Student.CSO_id
                r.save()

        students = Student.objects.filter(Community_id=community)
        generated_count = 0
        skipped_count = 0

        for student in students:
            # Check if report already exists for this term and year
            existing = Report.objects.filter(Student=student, Report_term=term, date_submitted__year=year).exists()
            if existing:
                skipped_count += 1
                continue

            Report.objects.create(
                Student=student,
                CSO=student.CSO_id,
                CSD=community.CSD,
                Report_term=term,
                status='Ready to begin',
                date_submitted=datetime.date(int(year), 1, 1)
            )
            generated_count += 1

        return Response({
            "detail": f"Report generation complete. Generated {generated_count} reports, skipped {skipped_count} existing reports.",
            "generated_count": generated_count,
            "skipped_count": skipped_count
        }, status=status.HTTP_201_CREATED)


class ReportDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        try:
            return Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return None

    def get(self, request, pk):
        report = self.get_object(pk)
        if not report:
            return Response({"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        report = self.get_object(pk)
        if not report:
            return Response({"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            staff = request.user.staff
        except ObjectDoesNotExist:
            return Response({"detail": "Only staff members can edit reports."}, status=status.HTTP_403_FORBIDDEN)

        role = (staff.account_type or '').lower()

        old_status = report.status
        new_status = request.data.get('status', old_status)

        # Update fields if provided
        if 'Content' in request.data:
            report.Content = request.data.get('Content')
        if 'Prayer_request' in request.data:
            report.Prayer_request = request.data.get('Prayer_request')
        if 'Photo' in request.data:
            report.Photo = request.data.get('Photo')
        if 'american_editor' in request.data:
            editor_id = request.data.get('american_editor')
            if editor_id:
                try:
                    report.american_editor = Staff.objects.get(pk=editor_id)
                except Staff.DoesNotExist:
                    pass

        report.status = new_status
        report.save()

        # Approval Pipeline notifications & emails
        if new_status != old_status:
            # 1. CSO submits to CSD -> status: Waiting for Approval
            if new_status.lower() == 'waiting for approval':
                if report.CSD:
                    Notification.objects.create(
                        recipient=report.CSD,
                        title="Report Ready for Review",
                        message=f"CSO {staff.full_name} has submitted the report for {report.Student.Full_name} for approval."
                    )
                    send_report_email(
                        recipient_email=report.CSD.email,
                        subject="Sponsorship Report Awaiting Approval",
                        message=f"Hello {report.CSD.full_name},\n\nThe sponsorship report for {report.Student.Full_name} is awaiting your approval. Please review it in the CSD Dashboard."
                    )

            # 2. CSD approves -> status: Waiting for US Approval
            elif new_status.lower() == 'waiting for us approval':
                # Notify the assigned American editor
                if report.american_editor:
                    Notification.objects.create(
                        recipient=report.american_editor,
                        title="Report Awaiting Final US Approval",
                        message=f"CSD {staff.full_name} has approved and assigned you the report for {report.Student.Full_name}."
                    )
                    send_report_email(
                        recipient_email=report.american_editor.email,
                        subject="Sponsorship Report Awaiting US Approval",
                        message=f"Hello {report.american_editor.full_name},\n\nThe sponsorship report for {report.Student.Full_name} has been approved by the CSD and is awaiting your final US approval."
                    )

            # 3. American approves -> status: Approved
            elif new_status.lower() == 'approved':
                # Notify CSO and CSD
                if report.CSO:
                    Notification.objects.create(
                        recipient=report.CSO,
                        title="Report Approved",
                        message=f"The report for {report.Student.Full_name} has been approved by the US team."
                    )
                    send_report_email(
                        recipient_email=report.CSO.email,
                        subject="Sponsorship Report Approved",
                        message=f"Hello {report.CSO.full_name},\n\nThe report for {report.Student.Full_name} has been approved by the US team and is now visible to the sponsor."
                    )
                if report.CSD:
                    Notification.objects.create(
                        recipient=report.CSD,
                        title="Report Approved",
                        message=f"The report for {report.Student.Full_name} has been approved by the US team."
                    )
                    send_report_email(
                        recipient_email=report.CSD.email,
                        subject="Sponsorship Report Approved",
                        message=f"Hello {report.CSD.full_name},\n\nThe report for {report.Student.Full_name} has been approved by the US team."
                    )

                # Send email to Sponsor (if sponsored)
                if report.Student.Sponsor_id:
                    sponsor = report.Student.Sponsor_id
                    send_report_email(
                        recipient_email=sponsor.Email,
                        subject=f"New Sponsorship Report Available: {report.Student.Full_name}",
                        message=f"Hello {sponsor.Full_name},\n\nA new sponsorship report is available for your sponsored child, {report.Student.Full_name}. Please log in to your Sponsor Dashboard to review it."
                    )

        serializer = ReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        report = self.get_object(pk)
        if not report:
            return Response({"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportCommentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            report = Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return Response({"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            staff = request.user.staff
        except ObjectDoesNotExist:
            return Response({"detail": "Only staff members can comment on reports."}, status=status.HTTP_403_FORBIDDEN)

        text = request.data.get('text')
        if not text:
            return Response({"detail": "Comment text is required."}, status=status.HTTP_400_BAD_REQUEST)

        comment = ReportComment.objects.create(
            report=report,
            author=staff,
            text=text
        )

        # Notify other stakeholders
        role = (staff.account_type or '').lower()
        recipients = []

        if 'cso' in role:
            if report.CSD:
                recipients.append(report.CSD)
            if report.american_editor:
                recipients.append(report.american_editor)
        elif 'csd' in role:
            if report.CSO:
                recipients.append(report.CSO)
            if report.american_editor:
                recipients.append(report.american_editor)
        elif 'american' in role:
            if report.CSO:
                recipients.append(report.CSO)
            if report.CSD:
                recipients.append(report.CSD)

        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                title=f"New Comment on Report for {report.Student.Full_name}",
                message=f"{staff.full_name} commented: \"{text[:60]}...\""
            )
            send_report_email(
                recipient_email=recipient.email,
                subject=f"New Comment: Report for {report.Student.Full_name}",
                message=f"Hello {recipient.full_name},\n\n{staff.full_name} has posted a comment on the report for {report.Student.Full_name}:\n\n\"{text}\"\n\nPlease log in to review and respond."
            )

        serializer = ReportCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SponsorStudentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            # Let's find the sponsor record linked to the logged-in user
            sponsor = Sponsor.objects.filter(User=request.user).first()
            if not sponsor:
                # If they are registered as Staff with Sponsor account type, we can find/create it
                try:
                    staff = request.user.staff
                except ObjectDoesNotExist:
                    staff = None
                
                # Try to create or find Sponsor
                import random
                sponsor_number = f"SP{random.randint(100000, 999999)}"
                while Sponsor.objects.filter(Sponsor_number=sponsor_number).exists():
                    sponsor_number = f"SP{random.randint(100000, 999999)}"

                sponsor = Sponsor.objects.create(
                    User=request.user,
                    staff=staff,
                    Full_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email,
                    Email=request.user.email,
                    Sponsor_number=sponsor_number
                )

            student = Student.objects.get(pk=pk)
        except Student.DoesNotExist:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        if student.Is_sponsored:
            return Response({"detail": "This student is already sponsored."}, status=status.HTTP_400_BAD_REQUEST)

        # Update student record
        student.Sponsor_id = sponsor
        student.Is_sponsored = True
        student.save()

        # Create Sponsorship record
        from datetime import date
        Sponsorship.objects.create(
            Sponsor_id=sponsor,
            Student_id=student,
            Date=date.today(),
            Status='Active'
        )

        # Send notifications
        title = "New Student Sponsored 🌟"
        message = f"Sponsor {sponsor.Full_name} has sponsored {student.Full_name}."

        # 1. Notify CSO
        if student.CSO_id:
            Notification.objects.create(recipient=student.CSO_id, title=title, message=message)
            send_report_email(student.CSO_id.email, title, message)

        # 2. Notify CSD
        if student.Community_id and student.Community_id.CSD:
            Notification.objects.create(recipient=student.Community_id.CSD, title=title, message=message)
            send_report_email(student.Community_id.CSD.email, title, message)

        # 3. Notify Americans
        americans = Staff.objects.filter(account_type__in=['american', 'american-staff'])
        for american in americans:
            Notification.objects.create(recipient=american, title=title, message=message)
            send_report_email(american.email, title, message)

        return Response({"detail": "Successfully sponsored student."}, status=status.HTTP_200_OK)





