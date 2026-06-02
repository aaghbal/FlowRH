"""
forms.py

This module contains the form classes used in the application.

Each form represents a specific functionality or data input in the
application. They are responsible for validating
and processing user input data.

Classes:
- YourForm: Represents a form for handling specific data input.

Usage:
from django import forms

class YourForm(forms.Form):
    field_name = forms.CharField()

    def clean_field_name(self):
        # Custom validation logic goes here
        pass
"""

import uuid
from datetime import date
from typing import Any

from django import forms
from django.contrib.auth.forms import UserCreationForm as UserForm
from django.contrib.auth.models import User
from django.forms import DateInput, ValidationError
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from base.methods import reload_queryset
from employee.filters import EmployeeFilter
from employee.models import Employee, EmployeeBankDetails
from horilla import horilla_middlewares
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget
from onboarding.models import CandidateTask, OnboardingStage, OnboardingTask
from recruitment.models import Candidate


class ModelForm(forms.ModelForm):
    """
    Overriding django default model form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(horilla_middlewares._thread_locals, "request", None)
        reload_queryset(self.fields)
        for _, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, (forms.DateInput)):
                field.initial = date.today()

            if isinstance(widget, (forms.DateInput)):
                field.widget.attrs.update({"class": "oh-input  w-100"})
            elif isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": field.label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": field.label,
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})
            try:
                self.fields["employee_id"].initial = request.user.employee_get
            except:
                pass

            try:
                self.fields["company_id"].initial = (
                    request.user.employee_get.get_company
                )
            except:
                pass


class UserCreationFormCustom(UserForm):
    """
    Overriding user creation form to apply some styles
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        for _, field in self.fields.items():
            widget = field.widget
            if isinstance(
                widget,
                (
                    forms.NumberInput,
                    forms.EmailInput,
                    forms.TextInput,
                    forms.PasswordInput,
                ),
            ):
                field.widget.attrs.update(
                    {
                        "class": "oh-input oh-input--password w-100",
                        "placeholder": field.label,
                    }
                )
            elif isinstance(widget, (forms.DateField)):
                field.widget.attrs.update({"class": "oh-input oh-calendar-input w-100"})
            elif isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": field.label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.empty_label = f"---Choose {field.label}---"
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": field.label,
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})


class OnboardingStageForm(ModelForm):
    """
    Form for OnboardingStage model
    """

    class Meta:
        """
        Meta class to add additional info
        """

        model = OnboardingStage
        fields = "__all__"
        exclude = ["sequence", "is_active"]


class OnboardingCandidateForm(ModelForm):
    """
    Form for Candidate model
    """

    class Meta:
        """
        Meta class for some additional options
        """

        model = Candidate
        fields = "__all__"
        exclude = (
            "stage_id",
            "assigned_manager",
            "confirmation",
            "hired",
            "referral",
            "portfolio",
            "canceled",
            "is_active",
            "resume",
            "schedule_date",
            "job_position_id",
        )
        widgets = {
            "joining_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "name": _("Full Name"),
            "email": _("Email"),
            "mobile": _("Mobile"),
        }


class UserCreationForm(UserCreationFormCustom):
    """
    Form for User model
    """

    class Meta:
        """
        Meta class to add some additional options
        """

        model = User
        fields = ["password1", "password2"]


class OnboardingViewTaskForm(ModelForm):
    """
    Form for OnboardingTask model
    """

    candidates = forms.ModelMultipleChoiceField(
        queryset=Candidate.objects.all(),
        # widget=forms.SelectMultiple(attrs={"class": "select2-hidden-accessible "}),
        required=False,
    )
    stage_id = forms.HiddenInput()
    task_title = forms.CharField(label=(_("Task title")))
    managers = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.all(),
        # widget=forms.SelectMultiple(attrs={"class": "select2-hidden-accessible "})
    )

    class Meta:
        """
        Meta class for some additional options
        """

        model = CandidateTask
        fields = "__all__"
        exclude = ["status", "candidate_id", "onboarding_task_id", "is_active"]

    def clean(self):
        for field_name, field_instance in self.fields.items():
            if isinstance(field_instance, HorillaMultiSelectField):
                self.errors.pop(field_name, None)
                if len(self.data.getlist(field_name)) < 1:
                    raise forms.ValidationError({field_name: "Thif field is required"})
                cleaned_data = super().clean()
                employee_data = self.fields[field_name].queryset.filter(
                    id__in=self.data.getlist(field_name)
                )
                cleaned_data[field_name] = employee_data
        cleaned_data = super().clean()
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["managers"] = HorillaMultiSelectField(
            queryset=Employee.objects.all(),
            widget=HorillaMultiSelectWidget(
                filter_route_name="employee-widget-filter",
                filter_class=EmployeeFilter,
                filter_instance_contex_name="f",
                filter_template_path="employee_filters.html",
                required=True,
                instance=self.instance,
            ),
            label="Task Managers",
        )
        reload_queryset(self.fields)
        stage = self.initial.get("stage_id")
        if stage:
            # Adjust the queryset based on the 'stage'
            candidate_ids = stage.candidate.all().values_list("candidate_id", flat=True)
            cand_queryset = Candidate.objects.filter(id__in=candidate_ids)
            self.fields["candidates"].queryset = cand_queryset
            self.fields["candidates"].initial = cand_queryset


class OnboardingTaskForm(ModelForm):
    """
    Form for OnboardingTaskModel
    """

    class Meta:
        """
        Meta class for add some additional options
        """

        model = OnboardingTask
        fields = "__all__"
        exclude = ["stage_id", "is_active"]
        widgets = {
            "candidates": forms.SelectMultiple(
                attrs={"class": "oh-select oh-select-2 w-100 select2-hidden-accessible"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_id"] = HorillaMultiSelectField(
            queryset=Employee.objects.all(),
            widget=HorillaMultiSelectWidget(
                filter_route_name="employee-widget-filter",
                filter_class=EmployeeFilter,
                filter_instance_contex_name="f",
                filter_template_path="employee_filters.html",
                required=True,
                instance=self.instance,
            ),
            label="Task Managers",
        )
        stage_id = self.initial.get("stage_id")
        if stage_id:
            stage = OnboardingStage.objects.get(id=stage_id)
            recruitment = stage.recruitment_id

            # Adjust the queryset based on the 'stage'
            stage_queryset = recruitment.onboarding_stage.all()
            self.fields["stage_id"].queryset = stage_queryset
            candidate_ids = stage.candidate.all().values_list("candidate_id", flat=True)
            cand_queryset = Candidate.objects.filter(id__in=candidate_ids)
            self.fields["candidates"].queryset = cand_queryset

    def clean(self):
        if isinstance(self.fields["employee_id"], HorillaMultiSelectField):
            ids = self.data.getlist("employee_id")
            if ids:
                self.errors.pop("employee_id", None)
        super().clean()


class OnboardingViewStageForm(ModelForm):
    """
    Form for OnboardingStageModel
    """

    verbose_name = "Stage"

    class Meta:
        """
        Meta class for add some additional options
        """

        model = OnboardingStage
        fields = ["stage_title", "employee_id", "is_final_stage"]
        labels = {
            "stage_title": _("Stage Title"),
            "is_final_stage": _("Is Final Stage"),
        }

    def __init__(self, *args, **kwargs):
        """
        Initializes the form with custom field settings and widgets.
        """
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["employee_id"] = HorillaMultiSelectField(
            queryset=Employee.objects.filter(is_active=True),
            widget=HorillaMultiSelectWidget(
                filter_route_name="employee-widget-filter",
                filter_class=EmployeeFilter,
                filter_instance_contex_name="f",
                filter_template_path="employee_filters.html",
                required=True,
                instance=self.instance,
            ),
            label="Stage Managers",
        )

        # Loop through form fields and generate unique IDs for their attributes
        for field_name, field in self.fields.items():
            unique_id = str(uuid.uuid4())  # You can customize the unique ID format

            # Set the widget's attributes with the unique ID
            field.widget.attrs.update({"id": unique_id})

    def as_p(self, *args, **kwargs):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html

    def clean(self):
        if isinstance(self.fields["employee_id"], HorillaMultiSelectField):
            ids = self.data.getlist("employee_id")
            if ids:
                self.errors.pop("employee_id", None)
        super().clean()


class EmployeeCreationForm(ModelForm):
    """
    Form for Employee Model
    """

    employee_first_name = forms.CharField(required=True, label=_("Prénom"))
    employee_last_name = forms.CharField(required=True, label=_("Nom"))
    email = forms.EmailField(required=True, label=_("Email"))
    phone = forms.CharField(required=True, label=_("Téléphone"))
    dob = forms.DateField(required=True, label=_("Date de naissance"), widget=DateInput(attrs={"type": "date"}))
    qualification = forms.CharField(required=True, label=_("CIN"))
    gender = forms.ChoiceField(
        required=True,
        label=_("Genre"),
        choices=[
            ('', '---Choose Gender---'),
            ('male', _('Homme')),
            ('female', _('Femme')),
        ]
    )

    class Meta:
        """
        Meta class to add some additional options
        """

        model = Employee
        fields = [
            "employee_first_name",
            "employee_last_name", 
            "email",
            "phone",
            "dob",
            "gender",
            "qualification"
        ]

    def clean(self):
        cleaned_data = super().clean()
        # Temporarily disable validation for debugging
        return cleaned_data


class BankDetailsCreationForm(ModelForm):
    """
    Form for BankDetailsCreationForm
    """

    bank_name = forms.CharField(required=True, label=_("Banque Nom"))
    account_number = forms.CharField(required=True, label=_("Compte Numéro"))

    class Meta:
        """
        Meta class to add some additional options
        """

        model = EmployeeBankDetails
        fields = "__all__"
        exclude = ["employee_id", "additional_info", "is_active"]
