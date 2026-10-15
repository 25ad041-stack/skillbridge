from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    LearningProgress,
    LearningRequest,
    LearningSession,
    Rating,
    Skill,
    StudentProfile,
)


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Full name")
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label="Full name")
    email = forms.EmailField()

    class Meta:
        model = StudentProfile
        fields = ("college", "bio", "interests")
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["email"].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.email = self.cleaned_data["email"]
        if commit:
            self.user.save(update_fields=["first_name", "email"])
        return profile


class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ("notifications_enabled", "notification_volume")
        widgets = {
            "notifications_enabled": forms.CheckboxInput(attrs={"class": "toggle-input"}),
            "notification_volume": forms.NumberInput(
                attrs={"type": "range", "min": 0, "max": 100, "step": 1, "class": "volume-slider"}
            ),
        }


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ("name", "category", "level", "description", "mode")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class LearningRequestForm(forms.ModelForm):
    class Meta:
        model = LearningRequest
        fields = ("message",)
        widgets = {"message": forms.Textarea(attrs={"rows": 3})}


class SessionForm(forms.ModelForm):
    class Meta:
        model = LearningSession
        fields = ("starts_at", "details")
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "details": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_starts_at(self):
        starts_at = self.cleaned_data["starts_at"]
        if starts_at <= timezone.now():
            raise ValidationError("Choose a date and time in the future.")
        return starts_at


class ProgressForm(forms.ModelForm):
    class Meta:
        model = LearningProgress
        fields = ("skill_name", "current_level", "target_level", "percent")
        widgets = {"percent": forms.NumberInput(attrs={"min": 0, "max": 100})}


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ("score", "feedback")
        widgets = {
            "score": forms.Select(choices=[(i, f"{i} / 5") for i in range(1, 6)]),
            "feedback": forms.Textarea(attrs={"rows": 4}),
        }
