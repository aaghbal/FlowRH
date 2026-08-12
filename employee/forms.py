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

import logging
import re
from datetime import date
from typing import Any

from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import DateInput, TextInput
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as trans

from base.methods import eval_validate, reload_queryset
from base.models import Site
from employee.models import (
    Actiontype,
    BonusPoint,
    CompanyDocument,
    CompanyDocumentCategory,
    DisciplinaryAction,
    Employee,
    EmployeeBankDetails,
    EmployeeGeneralSetting,
    EmployeeNote,
    EmployeeTag,
    EmployeeWorkInformation,
    NoteFiles,
    POLICY_DOCUMENT_EXTENSIONS,
    Policy,
    PolicyDocument,
    PolicyFolder,
    PolicyMultipleFile,
)
from horilla import horilla_middlewares
from horilla_audit.models import AccountBlockUnblock

logger = logging.getLogger(__name__)


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

            if isinstance(
                widget,
                (forms.NumberInput, forms.EmailInput, forms.TextInput, forms.FileInput),
            ):
                label = trans(field.label.title())
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = trans(field.label)
                field.empty_label = trans("---Choose {label}---").format(label=label)
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                if field.label is not None:
                    label = trans(field.label)
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": label,
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
                if self._meta.model.__name__ not in ["DisciplinaryAction"]:
                    self.fields["employee_id"].initial = request.user.employee_get
            except:
                pass

            try:
                self.fields["company_id"].initial = (
                    request.user.employee_get.get_company
                )
            except:
                pass


class UserForm(ModelForm):
    """
    Form for User model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        fields = ("groups",)
        model = User


class UserPermissionForm(ModelForm):
    """
    Form for User model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        fields = ("groups", "user_permissions")
        model = User


class EmployeeForm(ModelForm):
    """
    Form for Employee model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = Employee
        fields = "__all__"
        exclude = (
            "employee_user_id",
            "additional_info",
            "is_from_onboarding",
            "is_directly_converted",
            "is_active",
            "zip",
            "country",
            "state",
            "city",
            "address",
            "experience",
            "marital_status",
            "children",
            "emergency_contact",
            "emergency_contact_name",
            "emergency_contact_relation",
        )
        widgets = {
            "dob": TextInput(attrs={"type": "date", "id": "dob"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["email"].required = False
        self.fields["phone"].widget.attrs["autocomplete"] = "phone"
        self.fields["phone"].required = False
        # self.fields["address"].widget.attrs["autocomplete"] = "address"
        if instance := kwargs.get("instance"):
            # ----
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            # ----
            initial = {}
            if instance.dob is not None:
                initial["dob"] = instance.dob.strftime("%H:%M")
            kwargs["initial"] = initial
        else:
            self.initial = {"badge_id": self.get_next_badge_id()}

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/create_form/personal_info_as_p.html", context)

    def get_next_badge_id(self):
        """
        This method is used to generate badge id
        """
        from base.context_processors import get_initial_prefix
        from employee.methods.methods import get_ordered_badge_ids

        prefix = get_initial_prefix(None)["get_initial_prefix"]
        data = get_ordered_badge_ids()
        result = []
        try:
            for sublist in data:
                for item in sublist:
                    if isinstance(item, str) and item.lower().startswith(
                        prefix.lower()
                    ):
                        # Find the index of the item in the sublist
                        index = sublist.index(item)
                        # Check if there is a next item in the sublist
                        if index + 1 < len(sublist):
                            result = sublist[index + 1]
                            result = re.findall(r"[a-zA-Z]+|\d+|[^a-zA-Z\d\s]", result)

            if result:
                prefix = []
                incremented = False
                for item in reversed(result):
                    total_letters = len(item)
                    total_zero_leads = 0
                    for letter in item:
                        if letter == "0":
                            total_zero_leads = total_zero_leads + 1
                            continue
                        break

                    if total_zero_leads:
                        item = item[total_zero_leads:]
                    if isinstance(item, list):
                        item = item[-1]
                    if not incremented and isinstance(eval_validate(str(item)), int):
                        item = int(item) + 1
                        incremented = True
                    if isinstance(item, int):
                        item = "{:0{}d}".format(item, total_letters)
                    prefix.insert(0, str(item))
                prefix = "".join(prefix)
        except Exception as e:
            logger.exception(e)
            prefix = get_initial_prefix(None)["get_initial_prefix"]
        return prefix

    def clean_badge_id(self):
        """
        This method is used to clean the badge id
        """
        badge_id = self.cleaned_data.get("badge_id")
        if badge_id:
            # Check if there's another employee with the same badge_id
            queryset = Employee.objects.filter(badge_id=badge_id)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(trans("Badge ID must be unique."))
            if not re.search(r"\d", badge_id):
                raise forms.ValidationError(
                    trans("Badge ID must contain at least one digit.")
                )
        return badge_id


class EmployeeWorkInformationForm(ModelForm):
    """
    Form for EmployeeWorkInformation model
    """
    # Site is backed by the Site table (shared with recruitment/onboarding).
    location = forms.ModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label=_("Site"),
        empty_label=_("---Select Site---"),
        widget=forms.Select(attrs={"class": "oh-select oh-select-2 w-100"})
    )

    class Meta:
        """
        Meta class to add the additional info
        """
        model = EmployeeWorkInformation
        fields = (
            "department_id",
            "job_position_id",
            # "job_role_id",
            # "shift_id",
            # "work_type_id",
            # "employee_type_id",
            "reporting_manager_id",
            "company_id",
            "location",
            "email",
            "mobile",
            "numero_cimr",
            "societe",
            "affiliation_cnss",
            "affiliation_mut",
            "date_joining",
            # "contract_end_date",
            # "tags",
            # "basic_salary",
            # "salary_hour",
        )
        exclude = ("employee_id",)

        widgets = {
            "date_joining": DateInput(attrs={"type": "date"}),
            "contract_end_date": DateInput(attrs={"type": "date"}),
            "email": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Numéro de CNSS"}),
            "mobile": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Affiliation CIMR"}),
            "numero_cimr": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Numéro CIMR"}),
            "societe": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Société"}),
            "affiliation_cnss": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Affiliation CNSS"}),
            "affiliation_mut": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Affiliation MUT"}),
        }
        labels = {
            "email": trans("Numéro de CNSS"),
            "mobile": trans("Affiliation CIMR"),
            "numero_cimr": trans("Numéro CIMR"),
            "societe": trans("Société"),
            "affiliation_cnss": trans("Affiliation CNSS"),
            "affiliation_mut": trans("Affiliation MUT"),
            "reporting_manager_id": trans("Responsable"),
        }

    def __init__(self, *args, disable=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False

        self.fields["job_position_id"].widget.attrs.update(
            {
                "onchange": "jobChange($(this))",
            }
        )

        for field in self.fields:
            self.fields[field].widget.attrs["placeholder"] = self.fields[field].label
            if disable:
                self.fields[field].disabled = True
        field_names = {
            "Department": "department",
            "Job Position": "job_position",
            "Job Role": "job_role",
            "Work Type": "work_type",
            "Employee Type": "employee_type",
            "Shift": "employee_shift",
        }
        urls = {
            "Department": "#dynamicDept",
            "Job Position": "#dynamicJobPosition",
            "Job Role": "#dynamicJobRole",
            "Work Type": "#dynamicWorkType",
            "Employee Type": "#dynamicEmployeeType",
            "Shift": "#dynamicShift",
        }

        for label, field in self.fields.items():
            if isinstance(field, forms.ModelChoiceField) and field.label in field_names:
                if field.label is not None:
                    field_name = field_names.get(field.label)
                    if field.queryset.model != Employee and field_name:
                        translated_label = _(field.label)
                        empty_label = _("---Choose {label}---").format(
                            label=translated_label
                        )
                        self.fields[label] = forms.ChoiceField(
                            choices=[("", empty_label)]
                            + list(field.queryset.values_list("id", f"{field_name}")),
                            required=field.required,
                            label=translated_label,
                            initial=field.initial,
                            widget=forms.Select(
                                attrs={
                                    "class": "oh-select oh-select-2 select2-hidden-accessible",
                                    "onchange": f'onDynamicCreate(this.value,"{urls.get(field.label)}");',
                                }
                            ),
                        )
                        self.fields[label].choices += [
                            ("create", _("Create New {} ").format(translated_label))
                        ]

    def clean(self):
        cleaned_data = super().clean()
        if "employee_id" in self.errors:
            del self.errors["employee_id"]
        return cleaned_data

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/create_form/personal_info_as_p.html", context)


class EmployeeWorkInformationUpdateForm(ModelForm):
    """
    Form for EmployeeWorkInformation model
    """
    location = forms.ModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label=_("Site"),
        empty_label=_("---Select Site---"),
        widget=forms.Select(attrs={"class": "oh-select oh-select-2 w-100"})
    )

    class Meta:
        """
        Meta class to add the additional info
        """
        model = EmployeeWorkInformation
        fields = "__all__"
        exclude = ("employee_id",)

        widgets = {
            "date_joining": DateInput(attrs={"type": "date"}),
            "contract_end_date": DateInput(attrs={"type": "date"}),
            "contract_start_date": DateInput(attrs={"type": "date"}),
            "societe": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Société"}),
            "affiliation_cnss": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Affiliation CNSS"}),
            "affiliation_mut": forms.TextInput(attrs={"class": "oh-input w-100", "placeholder": "Affiliation MUT"}),
        }

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/create_form/personal_info_as_p.html", context)


class EmployeeBankDetailsForm(ModelForm):
    """
    Form for EmployeeBankDetails model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeBankDetails
        fields = (
            "bank_name",
            "account_number",
            "branch",
        )
        exclude = [
            "employee_id", 
            "is_active", 
            "additional_info",
            "any_other_code1",
            "address",
            "country",
            "state",
            "city",
            "any_other_code2",
        ]
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'oh-input w-100', 'required': False}),
            'account_number': forms.TextInput(attrs={'class': 'oh-input w-100', 'required': False}),
            'branch': forms.TextInput(attrs={'class': 'oh-input w-100', 'required': False}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['bank_name', 'account_number', 'branch']:
            self.fields[field_name].required = False

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/update_form/bank_info_as_p.html", context)


class EmployeeBankDetailsUpdateForm(ModelForm):
    """
    Form for EmployeeBankDetails model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeBankDetails
        fields = (
            "bank_name",
            "account_number",
            "branch",
        )
        exclude = [
            "employee_id", 
            "is_active", 
            "additional_info",
            "any_other_code1",
            "address",
            "country",
            "state",
            "city",
            "any_other_code2",
        ]
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'oh-input w-100', 'required': False}),
            'account_number': forms.TextInput(attrs={'class': 'oh-input w-100', 'required': False}),
            'branch': forms.TextInput(attrs={'class': 'oh-input w-100', 'required': False}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['bank_name', 'account_number', 'branch']:
            self.fields[field_name].required = False
            self.fields[field_name].widget.attrs["placeholder"] = self.fields[field_name].label

    def as_p(self, *args, **kwargs):
        context = {"form": self}
        return render_to_string("employee/update_form/bank_info_as_p.html", context)


excel_columns = [
    ("badge_id", trans("Badge ID")),
    ("employee_first_name", trans("First Name")),
    ("employee_last_name", trans("Last Name")),
    ("email", trans("Email")),
    ("phone", trans("Phone")),
    ("experience", trans("Experience")),
    ("gender", trans("Gender")),
    ("dob", trans("Date de naissance")),
    ("country", trans("Country")),
    ("state", trans("State")),
    ("city", trans("City")),
    ("address", trans("Address")),
    ("zip", trans("Zip Code")),
    ("qualification", trans("CIN")),
    ("marital_status", trans("Marital Status")),
    ("children", trans("Children")),
    ("is_active", trans("Is active")),
    ("emergency_contact", trans("Emergency Contact")),
    ("emergency_contact_name", trans("Emergency Contact Name")),
    ("emergency_contact_relation", trans("Emergency Contact Relation")),
    ("employee_work_info__email", trans("Work Email")),
    ("employee_work_info__mobile", trans("Work Phone")),
    ("employee_work_info__numero_cimr", trans("Numéro CIMR")),
    ("employee_work_info__societe", trans("Société")),
    ("employee_work_info__affiliation_cnss", trans("Affiliation CNSS")),
    ("employee_work_info__affiliation_mut", trans("Affiliation MUT")),
    ("employee_work_info__department_id", trans("Department")),
    ("employee_work_info__job_position_id", trans("Job Position")),
    ("employee_work_info__job_role_id", trans("Job Role")),
    ("employee_work_info__shift_id", trans("Shift")),
    ("employee_work_info__work_type_id", trans("Work Type")),
    ("employee_work_info__reporting_manager_id", trans("Reporting Manager")),
    ("employee_work_info__employee_type_id", trans("Employee Type")),
    ("employee_work_info__location", trans("Site")),
    ("employee_work_info__date_joining", trans("Date Joining")),
    ("employee_work_info__company_id", trans("Company")),
    ("employee_bank_details__bank_name", trans("Bank Name")),
    ("employee_bank_details__branch", trans("Branch")),
    ("employee_bank_details__account_number", trans("Account Number")),
    ("employee_bank_details__any_other_code1", trans("Bank Code #1")),
    ("employee_bank_details__any_other_code2", trans("Bank Code #2")),
    ("employee_bank_details__country", trans("Bank Country")),
    ("employee_bank_details__state", trans("Bank State")),
    ("employee_bank_details__city", trans("Bank City")),
]
fields_to_remove = [
    "badge_id",
    "employee_first_name",
    "employee_last_name",
    "is_active",
    "email",
    "phone",
    "employee_bank_details__account_number",
]


class EmployeeExportExcelForm(forms.Form):
    selected_fields = forms.MultipleChoiceField(
        choices=excel_columns,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "badge_id",
            "employee_first_name",
            "employee_last_name",
            "email",
            "phone",
            "gender",
            "employee_work_info__department_id",
            "employee_work_info__job_position_id",
            "employee_work_info__job_role_id",
            "employee_work_info__shift_id",
            "employee_work_info__work_type_id",
            "employee_work_info__reporting_manager_id",
            "employee_work_info__employee_type_id",
            "employee_work_info__company_id",
        ],
    )


class BulkUpdateFieldForm(forms.Form):
    update_fields = forms.MultipleChoiceField(
        choices=excel_columns, label=_("Select Fields to Update")
    )
    bulk_employee_ids = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        updated_choices = [
            (value, label)
            for value, label in self.fields["update_fields"].choices
            if value not in fields_to_remove
        ]
        self.fields["update_fields"].choices = updated_choices
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = (
                "oh-select oh-select-2 select2-hidden-accessible oh-input w-100"
            )


class EmployeeNoteForm(ModelForm):
    """
    Form for EmployeeNote model
    """

    class Meta:
        """
        Meta class to add the additional info
        """

        model = EmployeeNote
        fields = ("description",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note_files"] = MultipleFileField(label="files")
        self.fields["note_files"].required = False

    def save(self, commit: bool = ...) -> Any:
        attachement = []
        multiple_attachment_ids = []
        attachements = None
        if self.files.getlist("note_files"):
            attachements = self.files.getlist("note_files")
            self.instance.attachement = attachements[0]
            multiple_attachment_ids = []

            for attachement in attachements:
                file_instance = NoteFiles()
                file_instance.files = attachement
                file_instance.save()
                multiple_attachment_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.note_files.add(*multiple_attachment_ids)
        return instance, multiple_attachment_ids


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        if len(result) == 0:
            result = [[]]
        return result[0]


class PolicyForm(ModelForm):
    """
    PolicyForm
    """

    class Meta:
        model = Policy
        fields = "__all__"
        exclude = ["attachments", "is_active"]
        widgets = {
            "body": forms.Textarea(
                attrs={"data-summernote": "", "style": "display:none;"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attachment"] = MultipleFileField(
            label="Attachements", required=False
        )

    def save(self, *args, commit=True, **kwargs):
        attachemnt = []
        multiple_attachment_ids = []
        attachemnts = None
        if self.files.getlist("attachment"):
            attachemnts = self.files.getlist("attachment")
            multiple_attachment_ids = []
            for attachemnt in attachemnts:
                file_instance = PolicyMultipleFile()
                file_instance.attachment = attachemnt
                file_instance.save()
                multiple_attachment_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.attachments.add(*multiple_attachment_ids)
        return instance, attachemnts


class PolicyFolderForm(ModelForm):
    """
    Form to create / rename a policy folder. The parent folder is not part
    of the form, it comes from the folder currently opened in the explorer.
    """

    class Meta:
        model = PolicyFolder
        fields = [
            "name",
            "description",
            "is_visible_to_all",
            "specific_employees",
            "company_id",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["specific_employees"].widget.attrs.update(
            {"class": "oh-select oh-select-2"}
        )
        self.fields["company_id"].widget.attrs.update(
            {"class": "oh-select oh-select-2"}
        )


class PolicyDocumentForm(ModelForm):
    """
    Form to upload one or more documents (PDF, Word, Excel) inside a
    policy folder.
    """

    class Meta:
        model = PolicyDocument
        fields = ["attachment"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attachment"] = MultipleFileField(
            label=_("Fichiers"), required=True
        )
        self.fields["attachment"].widget.attrs.update(
            {"accept": ",".join(f".{ext}" for ext in POLICY_DOCUMENT_EXTENSIONS)}
        )


class CompanyDocumentForm(ModelForm):
    """
    Form to upload a company document.
    """

    class Meta:
        model = CompanyDocument
        fields = ["title", "category", "document", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["document"].widget.attrs.update(
            {"accept": ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.zip"}
        )


class CompanyDocumentCategoryForm(ModelForm):
    """
    Form to create/update a company document category.
    """

    class Meta:
        model = CompanyDocumentCategory
        fields = ["name"]


class BonusPointAddForm(ModelForm):
    class Meta:
        model = BonusPoint
        fields = ["points", "reason"]
        widgets = {
            "reason": forms.TextInput(attrs={"required": "required"}),
        }


class BonusPointRedeemForm(ModelForm):
    class Meta:
        model = BonusPoint
        fields = ["points"]

    def clean(self):
        cleaned_data = super().clean()
        available_points = BonusPoint.objects.filter(
            employee_id=self.instance.employee_id
        ).first()
        if available_points.points < cleaned_data["points"]:
            raise forms.ValidationError({"points": "Not enough bonus points to redeem"})
        if cleaned_data["points"] <= 0:
            raise forms.ValidationError(
                {"points": "Points must be greater than zero to redeem."}
            )


class DisciplinaryActionForm(ModelForm):
    class Meta:
        model = DisciplinaryAction
        fields = "__all__"
        exclude = ["objects", "is_active"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
        }

    action = forms.ModelChoiceField(
        queryset=Actiontype.objects.all(),
        label=_("Action"),
        widget=forms.Select(
            attrs={
                "class": "oh-select oh-select-2 select2-hidden-accessible",
                "onchange": "actionTypeChange($(this))",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        action_choices = [("", _("---Choose Action---"))] + list(
            self.fields["action"].queryset.values_list("id", "title")
        )
        self.fields["action"].choices = action_choices
        if self.instance.pk is None:
            self.fields["action"].choices += [("create", _("Create new action type "))]

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("common_form.html", context)
        return table_html


class ActiontypeForm(ModelForm):
    class Meta:
        model = Actiontype
        fields = "__all__"
        exclude = ["is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["action_type"].widget.attrs.update(
            {
                "onchange": "actionChange($(this))",
            }
        )


class EmployeeTagForm(ModelForm):
    """
    Employee Tags form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeTag
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {"color": TextInput(attrs={"type": "color", "style": "height:50px"})}


class EmployeeGeneralSettingPrefixForm(forms.ModelForm):

    class Meta:

        model = EmployeeGeneralSetting
        exclude = ["objects"]
        widgets = {
            "badge_id_prefix": forms.TextInput(attrs={"class": "oh-input w-100"}),
            "company_id": forms.Select(attrs={"class": "oh-select oh-select-2 w-100"}),
        }
