from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import uuid

class CustomUserManager(BaseUserManager):
    def _create_user(self, email, password, first_name, last_name, **extra_fields):
        if not email:
            raise ValueError('Email must be provided')
        if not password:
            raise ValueError('Password not provided')

        user = self.model(
            email = self.normalize_email(email),
            first_name = first_name,
            last_name = last_name,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, email, password, first_name, last_name, **extra_fields):
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, first_name, last_name, **extra_fields)
    
    def create_superuser(self, email, password, first_name, last_name, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, first_name, last_name, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(db_index=True, unique=True, max_length=200, null=True, blank=True)
    first_name = models.CharField(max_length=200, null=True, blank=True)
    last_name = models.CharField(max_length=200, null=True, blank=True)
    address = models.CharField(max_length=250, blank=True, null=True)

    is_staff = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Staff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff')
    full_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    job_title = models.CharField(max_length=255, null=True, blank=True)
    community = models.UUIDField(null=True, blank=True)
    station = models.CharField(max_length=255, null=True, blank=True)
    account_type = models.CharField(max_length=100, null=True, blank=True)
    address_line_1 = models.TextField(null=True, blank=True)
    address_line_2 = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name if self.full_name else f"Staff - {self.id}"


class PasswordResetOTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OTP for {self.email}: {self.otp}"


class Sponsor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    User = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='User')
    Full_name = models.CharField(max_length=255, null=True, blank=True)
    Email = models.EmailField(max_length=255, null=True, blank=True)
    Phone_number = models.CharField(max_length=50, null=True, blank=True)
    Sponsor_number = models.CharField(max_length=100, null=True, blank=True)
    Address_line_1 = models.TextField(null=True, blank=True)
    Address_line_2 = models.TextField(null=True, blank=True)
    Country = models.CharField(max_length=100, null=True, blank=True)
    State = models.CharField(max_length=100, null=True, blank=True)
    City = models.CharField(max_length=100, null=True, blank=True)
    Zip_code = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.Full_name if self.Full_name else f"Sponsor - {self.id}"


class Community(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Name = models.CharField(max_length=255, null=True, blank=True)
    CSD = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, db_column='CSD', related_name='managed_communities')
    Headmaster = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, db_column='Headmaster', related_name='led_communities')
    Created_at = models.DateTimeField(auto_now_add=True)
    Updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.Name if self.Name else f"Community - {self.id}"


class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Student_number = models.IntegerField(null=True, blank=True, unique=True)
    Full_name = models.CharField(max_length=255, null=True, blank=True)
    Date_of_birth = models.CharField(max_length=100, null=True, blank=True)
    Gender = models.CharField(max_length=10, null=True, blank=True)
    Current_grade = models.IntegerField(null=True, blank=True)
    Enrollment_term = models.CharField(max_length=100, null=True, blank=True)
    Profile_photo = models.ImageField(upload_to='student_photos/', null=True, blank=True)
    Headshot = models.ImageField(upload_to='student_headshots/', null=True, blank=True)
    Bio = models.TextField(null=True, blank=True)
    Is_sponsored = models.BooleanField(default=False)
    Fee_paying = models.BooleanField(default=False)
    Sponsor_id = models.ForeignKey(Sponsor, on_delete=models.SET_NULL, null=True, blank=True, db_column='Sponsor_id', related_name='sponsored_students')
    Community_id = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True, db_column='Community_id', related_name='students')
    CSO_id = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, db_column='CSO_id', related_name='cso_students')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.Full_name if self.Full_name else f"Student - {self.id}"


class DemographicHealthDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Living_parents = models.CharField(max_length=255, null=True, blank=True)
    Mother_relationship = models.CharField(max_length=255, null=True, blank=True)
    Father_relationship = models.CharField(max_length=255, null=True, blank=True)
    Siblings = models.IntegerField(null=True, blank=True)
    Distance_to_school = models.IntegerField(null=True, blank=True)
    Meals_per_week = models.IntegerField(null=True, blank=True)
    People_in_the_house = models.IntegerField(null=True, blank=True)
    People_in_school = models.IntegerField(null=True, blank=True)
    Reliable_income = models.IntegerField(null=True, blank=True)
    can_read = models.IntegerField(null=True, blank=True)
    Has_vehicle = models.BooleanField(default=False)
    Has_electricity = models.BooleanField(default=False)
    Has_water = models.BooleanField(default=False)
    Distance_to_water = models.IntegerField(null=True, blank=True)
    HIV_status = models.BooleanField(default=False)
    Has_disability = models.BooleanField(default=False)
    Demographic_comments = models.TextField(null=True, blank=True)
    Student = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='Student', related_name='demographics')
    Created_at = models.DateTimeField(auto_now_add=True)
    Updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Demographics for {self.Student.Full_name}" if self.Student else f"Demographics - {self.id}"


class GuardianInformation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Guardian_name = models.CharField(max_length=255, null=True, blank=True)
    Guardian_phone_number = models.CharField(max_length=50, null=True, blank=True)
    Guardian_NRC = models.CharField(max_length=100, null=True, blank=True)
    Primary_caretaker = models.CharField(max_length=255, null=True, blank=True)
    Caretaker_occupation = models.CharField(max_length=255, null=True, blank=True)
    Highest_education = models.CharField(max_length=255, null=True, blank=True)
    Can_read = models.BooleanField(default=False)
    Guardian_comments = models.TextField(null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='student', related_name='guardians')
    Created_at = models.DateTimeField(auto_now_add=True)
    Updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Guardian {self.Guardian_name} for {self.student.Full_name}" if self.student else f"Guardian - {self.id}"


class HealthConditions(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Condition_name = models.CharField(max_length=255, null=True, blank=True)
    Condition_description = models.TextField(null=True, blank=True)
    Condition_status = models.CharField(max_length=100, null=True, blank=True)
    Student = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='Student', related_name='health_conditions')
    Created_at = models.DateTimeField(auto_now_add=True)
    Updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Health Condition {self.Condition_name} for {self.Student.Full_name}" if self.Student else f"Condition - {self.id}"


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Student = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='Student', related_name='reports')
    Content = models.TextField(null=True, blank=True)
    Prayer_request = models.TextField(null=True, blank=True)
    Photo = models.ImageField(upload_to='report_photos/', null=True, blank=True)
    CSO = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, db_column='CSO', related_name='cso_reports')
    CSD = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, db_column='CSD', related_name='csd_reports')
    American_approver = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, db_column='American_approver', related_name='american_approved_reports')
    Report_term = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    date_submitted = models.DateField(null=True, blank=True)
    is_Zambian_approved = models.BooleanField(default=False)
    is_american_approved = models.BooleanField(default=False)
    Created_at = models.DateTimeField(auto_now_add=True)
    Updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report for {self.Student.Full_name} ({self.Report_term})" if self.Student else f"Report - {self.id}"


class Sponsorship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Sponsor_id = models.ForeignKey(Sponsor, on_delete=models.CASCADE, db_column='Sponsor_id', related_name='sponsorships')
    Student_id = models.ForeignKey(Student, on_delete=models.CASCADE, db_column='Student_id', related_name='sponsorships')
    Payment_type = models.CharField(max_length=100, null=True, blank=True)
    Date = models.DateField(null=True, blank=True)
    Due_date = models.DateField(null=True, blank=True)
    Description = models.TextField(null=True, blank=True)
    Amount = models.CharField(max_length=100, null=True, blank=True)
    Status = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Sponsorship by {self.Sponsor_id.Full_name} for {self.Student_id.Full_name}" if (self.Sponsor_id and self.Student_id) else f"Sponsorship - {self.id}"


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    Full_name = models.CharField(max_length=255, null=True, blank=True)
    Email = models.EmailField(max_length=255, null=True, blank=True)
    Date = models.DateField(null=True, blank=True)
    Description = models.TextField(null=True, blank=True)
    Amount = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Transaction {self.id} by {self.Full_name} ({self.Amount})"


class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    profession = models.CharField(max_length=255, null=True, blank=True)
    quote = models.TextField(null=True, blank=True)
    story = models.TextField(null=True, blank=True)
    impact = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='story_images/', null=True, blank=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Story'
        verbose_name_plural = 'Stories'

    def __str__(self):
        return self.name if self.name else f"Story - {self.id}"




