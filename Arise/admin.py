from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Staff, PasswordResetOTP, Sponsor, SponsorSignUpOTP, Community, Student,
    DemographicHealthDetails, GuardianInformation, HealthConditions,
    Report, Sponsorship, Transaction, Story, AcademicRecord,
    LessonPlan, WeeklyReport, Notification, ReportComment
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'address', 'is_staff', 'is_active', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'address')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    def save_model(self, request, obj, form, change):
        from django.contrib.auth.hashers import identify_hasher
        try:
            identify_hasher(obj.password)
        except ValueError:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'job_title', 'station', 'is_active', 'is_complete')
    search_fields = ('full_name', 'email', 'phone_number', 'job_title', 'station')
    list_filter = ('is_active', 'is_complete', 'account_type', 'country', 'state')

@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp', 'created_at')
    search_fields = ('email', 'otp')
    readonly_fields = ('created_at',)

@admin.register(SponsorSignUpOTP)
class SponsorSignUpOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp', 'created_at')
    search_fields = ('email', 'otp')
    readonly_fields = ('created_at',)

@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ('Full_name', 'Email', 'Phone_number', 'Sponsor_number', 'Country', 'City', 'profile_photo', 'staff')
    search_fields = ('Full_name', 'Email', 'Phone_number', 'Sponsor_number')
    list_filter = ('Country', 'State', 'City')

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('Name', 'CSD', 'Headmaster', 'Created_at')
    search_fields = ('Name',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('Student_number', 'Full_name', 'Gender', 'Current_grade', 'Is_sponsored', 'Fee_paying', 'Community_id')
    search_fields = ('Full_name', 'Student_number')
    list_filter = ('Gender', 'Current_grade', 'Is_sponsored', 'Fee_paying', 'Community_id')

@admin.register(DemographicHealthDetails)
class DemographicHealthDetailsAdmin(admin.ModelAdmin):
    list_display = ('Student', 'Living_parents', 'Siblings', 'Distance_to_school', 'Reliable_income')
    search_fields = ('Student__Full_name',)

@admin.register(GuardianInformation)
class GuardianInformationAdmin(admin.ModelAdmin):
    list_display = ('Guardian_name', 'Guardian_phone_number', 'student', 'Primary_caretaker')
    search_fields = ('Guardian_name', 'student__Full_name')

@admin.register(HealthConditions)
class HealthConditionsAdmin(admin.ModelAdmin):
    list_display = ('Condition_name', 'Condition_status', 'Student')
    search_fields = ('Condition_name', 'Student__Full_name')
    list_filter = ('Condition_status',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('Student', 'Report_term', 'status', 'CSO', 'CSD', 'is_Zambian_approved', 'is_american_approved', 'date_submitted')
    search_fields = ('Student__Full_name', 'Report_term')
    list_filter = ('status', 'is_Zambian_approved', 'is_american_approved', 'Report_term')

@admin.register(Sponsorship)
class SponsorshipAdmin(admin.ModelAdmin):
    list_display = ('Sponsor_id', 'Student_id', 'Payment_type', 'Date', 'Due_date', 'Amount', 'Status')
    search_fields = ('Sponsor_id__Full_name', 'Student_id__Full_name')
    list_filter = ('Status', 'Payment_type')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('Full_name', 'Email', 'Amount', 'status', 'Date')
    search_fields = ('Full_name', 'Email')
    list_filter = ('status', 'Date')

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'graduation_year', 'title', 'profession')
    search_fields = ('name', 'title', 'profession')
    list_filter = ('graduation_year',)

@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'year', 'grade', 'subject', 'mt1', 'et1', 'mt2', 'et2', 'mt3', 'et3')
    search_fields = ('student__Full_name', 'grade', 'subject')
    list_filter = ('year', 'grade', 'subject')


@admin.register(LessonPlan)
class LessonPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'grade', 'subject', 'week_number', 'status')
    search_fields = ('title', 'teacher__full_name', 'grade', 'subject')
    list_filter = ('status', 'grade', 'subject')


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'week_ending_date', 'created_at')
    search_fields = ('teacher__full_name', 'week_ending_date')
    list_filter = ('week_ending_date',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at')
    search_fields = ('recipient__full_name', 'title')
    list_filter = ('is_read', 'created_at')


@admin.register(ReportComment)
class ReportCommentAdmin(admin.ModelAdmin):
    list_display = ('report', 'author', 'created_at')
    search_fields = ('report__Student__Full_name', 'author__full_name', 'text')
    list_filter = ('created_at',)






