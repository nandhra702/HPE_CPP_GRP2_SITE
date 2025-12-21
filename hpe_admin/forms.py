from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
import json
from judge.admin.contest import ContestForm, DashboardButtonWidget
from judge.admin.problem import ProblemForm
from judge.admin.mcq import MCQQuestionForm
from judge.models import Profile, Problem, Language
from judge.widgets import AdminHeavySelect2MultipleWidget, AdminSelect2MultipleWidget, AdminHeavySelect2Widget, CheckboxSelectMultipleWithSelectAll

class ContestParticipantUploadForm(forms.Form):
    participants_csv = forms.FileField(
        label=_('Upload Participants CSV'),
        help_text=_('CSV format: username,email (optional: password)'),
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        required=False
    )

class HPEContestForm(ContestForm):
    participants_csv = forms.FileField(
        label=_('Upload Participants CSV'),
        help_text=mark_safe(_(
            'Upload a CSV file containing participant emails.<br>'
            '<small>Usernames will be automatically generated from emails if not provided.</small><br>'
            '<details>'
            '<summary><strong>View Example CSV Format</strong></summary>'
            '<pre style="margin-top: 5px; background: #f5f5f5; padding: 5px; border-radius: 4px;">'
            '<strong>Option 1: Email only</strong>\n'
            'john@example.com\n'
            'jane@example.com\n\n'
            '<strong>Option 2: Email and Username</strong>\n'
            'john@example.com,john_doe\n'
            'jane@example.com,jane_smith'
            '</pre>'
            '</details>'
        )),
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        required=False
    )

    def __init__(self, *args, **kwargs):
        # Skip ContestForm.__init__ to avoid KeyErrors on missing fields (banned_users, etc.)
        # Call ModelForm.__init__ directly
        super(ContestForm, self).__init__(*args, **kwargs)
        
        # Re-implement necessary logic from ContestForm.__init__
        if self.instance and self.instance.pk:
            # Load existing selections
            p_data = []
            for cp in self.instance.contest_problems.select_related('problem', 'problem__group').order_by('order'):
                p_data.append({
                    'id': cp.problem_id,
                    'code': cp.problem.code,
                    'name': cp.problem.name,
                    'points': cp.points,
                    'partial': cp.partial,
                    'is_pretested': cp.is_pretested,
                    'max_submissions': cp.max_submissions,
                    'output_prefix_override': cp.output_prefix_override,
                    'order': cp.order,
                    'group': cp.problem.group.full_name if cp.problem.group else 'Uncategorized'
                })
            
            m_data = []
            for cm in self.instance.contest_mcqs.select_related('mcq_question').order_by('order'):
                m_data.append({
                    'id': cm.mcq_question_id,
                    'code': cm.mcq_question.code,
                    'name': cm.mcq_question.description[:50] + '...' if len(cm.mcq_question.description) > 50 else cm.mcq_question.description,
                    'points': cm.points,
                    'order': cm.order,
                })
                
            self.fields['contest_problems_json'].initial = json.dumps(p_data)
            self.fields['contest_mcqs_json'].initial = json.dumps(m_data)
            self.fields['contest_randomization_json'].initial = json.dumps(self.instance.randomization_config)

    def clean(self):
        # Skip ContestForm.clean which expects 'banned_users'
        # Go directly to ModelForm.clean
        cleaned_data = super(ContestForm, self).clean()
        return cleaned_data

class HPEProblemForm(ProblemForm):
    def __init__(self, *args, **kwargs):
        # Skip ProblemForm.__init__ if it tries to access fields we excluded
        # For simplicity, we just skip it entirely and call standard ModelForm init
        # But we do want widgets if the fields exist.
        # ProblemForm sets widgets for: authors, curators, testers, banned_users, change_message
        # We include authors, testers. Exclude curators, banned_users.
        
        # We can't easily selectively call parts of super().__init__.
        # So we replicate the necessary parts here.
        super(ProblemForm, self).__init__(*args, **kwargs)
        
        if 'authors' in self.fields:
            self.fields['authors'].widget.can_add_related = False
        if 'testers' in self.fields:
            self.fields['testers'].widget.can_add_related = False
        if 'change_message' in self.fields:
             self.fields['change_message'].widget.attrs.update({
                'placeholder': _('Describe the changes you made (optional)'),
            })
        
        # Rename 'group' to 'Difficulty'
        if 'group' in self.fields:
            self.fields['group'].label = _('Difficulty')
            self.fields['group'].help_text = _('Select difficulty level: Easy, Medium, or Hard')
            self.fields['group'].required = True

class HPEMCQForm(MCQQuestionForm):
    def __init__(self, *args, **kwargs):
        # Same strategy as ProblemForm
        super(MCQQuestionForm, self).__init__(*args, **kwargs)
        
        if 'authors' in self.fields:
            self.fields['authors'].widget.can_add_related = False
        if 'change_message' in self.fields:
            self.fields['change_message'].widget.attrs.update({
                'placeholder': _('Describe the changes you made (optional)'),
            })
        
        # Add LaTeX help text to description field
        if 'description' in self.fields:
            self.fields['description'].help_text = mark_safe(_(
                'The question text. Supports <b>Markdown</b> and <b>LaTeX</b> math.<br>'
                '<small>LaTeX examples: <code>$x^2$</code> for inline, <code>$$\\frac{a}{b}$$</code> for display</small>'
            ))

class HPEProblemBulkUploadForm(forms.Form):
    creators = forms.ModelMultipleChoiceField(
        label=_('Creators'),
        queryset=Profile.objects.all(),
        widget=AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
        required=True,
        help_text=_('These users will be able to edit the problem, and be listed as authors. '
                    'Hold down "Control", or "Command" on a Mac, to select more than one.')
    )
    testers = forms.ModelMultipleChoiceField(
        label=_('Testers'),
        queryset=Profile.objects.all(),
        widget=AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
        required=False,
        help_text=_('These users will be able to view the private problem, but not edit it. '
                    'Hold down "Control", or "Command" on a Mac, to select more than one.')
    )
    allowed_languages = forms.ModelMultipleChoiceField(
        label=_('Allowed languages'),
        queryset=Language.objects.all(),
        widget=CheckboxSelectMultipleWithSelectAll,
        required=False,
        help_text=_('List of allowed submission languages.')
    )
    csv_file = forms.FileField(
        label=_('CSV/Excel File'),
        help_text=mark_safe(_(
            '<b>Accepts:</b> .csv or .xlsx files<br>'
            'Format: Name, Body, Constraints, Time Limit (s), Memory Limit (kb), <b>Difficulty</b>, <b>Solution</b>, Test Cases...<br>'
            '<b>Difficulty</b>: Required. Must be <code>easy</code>, <code>medium</code>, or <code>hard</code>.<br>'
            '<b>Solution</b>: Optional. Text for the editorial.<br>'
            'Test Cases: Input1, Output1, Input2, Output2, etc.<br>'
            '<small>Example: "Sum", "Find A+B", "none", 1, 65536, "easy", "This is the solution", "1 2", "3", "5 5", "10"</small>'
        )),
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx'])]
    )


class HPEMCQBulkUploadForm(forms.Form):
    """Form for bulk uploading MCQ questions via CSV/Excel"""
    creators = forms.ModelMultipleChoiceField(
        label=_('Creators'),
        queryset=Profile.objects.all(),
        widget=AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
        required=False,
        help_text=_('Users who can edit these questions. Hold down "Control", or "Command" on a Mac, to select more than one.')
    )
    csv_file = forms.FileField(
        label=_('CSV/Excel File'),
        help_text=mark_safe(_(
            '<b>Accepts:</b> .csv or .xlsx files<br>'
            'Format: Question Text, Option1, Option2, Option3, Option4, <b>Answer(s)</b>...<br>'
            '<b>Answer columns:</b> Use the actual answer text (must match an option exactly).<br>'
            '<small>Example: "What is 2+2?", "3", "4", "5", "6", "4"</small><br>'
            '<small>Multi-answer: "Select primes", "2", "3", "4", "6", "2", "3"</small>'
        )),
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx'])]
    )
