from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from .models import Staff, Story, Student, GuardianInformation, DemographicHealthDetails, HealthConditions, Report, LessonPlan, WeeklyReport, Notification, ReportComment

class S3ImageURLField(serializers.Field):
    def __init__(self, upload_to='', **kwargs):
        self.upload_to = upload_to
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            return data
        if hasattr(data, 'name') and hasattr(data, 'read'):
            return data
        if not data:
            return None
        raise serializers.ValidationError("Invalid image data. Must be a URL or file.")

    def to_representation(self, value):
        return value


class StorySerializer(serializers.ModelSerializer):
    image = S3ImageURLField(upload_to='story_images', required=False, allow_null=True)

    class Meta:
        model = Story
        fields = '__all__'

class GuardianInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardianInformation
        fields = '__all__'

class DemographicHealthDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemographicHealthDetails
        fields = '__all__'

class HealthConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthConditions
        fields = '__all__'

class ReportCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)

    class Meta:
        model = ReportComment
        fields = '__all__'


class ReportSerializer(serializers.ModelSerializer):
    Photo = S3ImageURLField(upload_to='report_photos', required=False, allow_null=True)
    comments = ReportCommentSerializer(many=True, read_only=True)
    cso_name = serializers.CharField(source='CSO.full_name', read_only=True)
    cso_email = serializers.CharField(source='CSO.email', read_only=True, allow_null=True)
    csd_name = serializers.CharField(source='CSD.full_name', read_only=True)
    csd_email = serializers.CharField(source='CSD.email', read_only=True, allow_null=True)
    american_editor_name = serializers.CharField(source='american_editor.full_name', read_only=True)
    american_editor_email = serializers.CharField(source='american_editor.email', read_only=True, allow_null=True)
    student_name = serializers.CharField(source='Student.Full_name', read_only=True)
    student_school = serializers.CharField(source='Student.Community_id.Name', read_only=True)

    class Meta:
        model = Report
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    Community_name = serializers.CharField(source='Community_id.Name', read_only=True)
    CSO_name = serializers.CharField(source='CSO_id.full_name', read_only=True)
    Sponsor_email = serializers.CharField(source='Sponsor_id.Email', read_only=True, allow_null=True)
    Sponsor_name = serializers.CharField(source='Sponsor_id.Full_name', read_only=True, allow_null=True)
    guardians = GuardianInformationSerializer(many=True, read_only=True)
    demographics = DemographicHealthDetailsSerializer(many=True, read_only=True)
    health_conditions = HealthConditionsSerializer(many=True, read_only=True)
    reports = ReportSerializer(many=True, read_only=True)
    Profile_photo = S3ImageURLField(upload_to='student_photos', required=False, allow_null=True)
    Headshot = S3ImageURLField(upload_to='student_headshots', required=False, allow_null=True)

    class Meta:
        model = Student
        fields = '__all__'




class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        user = self.user
        staff_data = None
        try:
            staff = user.staff
        except ObjectDoesNotExist:
           
            staff = Staff.objects.create(
                user=user,
                email=user.email,
                full_name=f"{user.first_name} {user.last_name}".strip() if (user.first_name or user.last_name) else user.email,
                account_type="Sponsor"  # default account type
            )
        
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
        
        data['staff'] = staff_data
        return data


class LessonPlanSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)

    class Meta:
        model = LessonPlan
        fields = '__all__'


class WeeklyReportSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    teacher_station = serializers.CharField(source='teacher.station', read_only=True)

    class Meta:
        model = WeeklyReport
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

