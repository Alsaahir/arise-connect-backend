from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.exceptions import ObjectDoesNotExist
from .models import Staff, PasswordResetOTP, Story, Student, Community, Sponsor, SponsorSignUpOTP
from .serializers import StorySerializer, StudentSerializer



import string
import random
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


class UpdateStaffProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        try:
            staff = user.staff
        except ObjectDoesNotExist:
            return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

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
            "is_complete": staff.is_complete
        }, status=status.HTTP_200_OK)


class CreateStaffView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

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
            "profile_image": staff.profile_image.url if staff.profile_image else None,
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




