from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from .models import Staff, Story, Student, GuardianInformation, DemographicHealthDetails, HealthConditions, Report

class StorySerializer(serializers.ModelSerializer):
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

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    Community_name = serializers.CharField(source='Community_id.Name', read_only=True)
    CSO_name = serializers.CharField(source='CSO_id.full_name', read_only=True)
    guardians = GuardianInformationSerializer(many=True, read_only=True)
    demographics = DemographicHealthDetailsSerializer(many=True, read_only=True)
    health_conditions = HealthConditionsSerializer(many=True, read_only=True)
    reports = ReportSerializer(many=True, read_only=True)

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
            "is_active": staff.is_active,
            "is_complete": staff.is_complete,
        }
        
        data['staff'] = staff_data
        return data
