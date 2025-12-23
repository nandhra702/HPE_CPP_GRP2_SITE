from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from datetime import timedelta
import json
from judge.admin.contest import ContestForm, DashboardButtonWidget
from judge.admin.problem import ProblemForm
from judge.admin.mcq import MCQQuestionForm
from judge.models import Profile, Problem, Language
from judge.widgets import AdminHeavySelect2MultipleWidget, AdminSelect2MultipleWidget, AdminHeavySelect2Widget, CheckboxSelectMultipleWithSelectAll


class DurationDropdownWidget(forms.Widget):
    """
    A custom widget that displays three dropdowns for Hours, Minutes, and Seconds
    to input a duration value in a user-friendly way.
    """
    template_name = 'django/forms/widgets/text.html'  # Fallback, we override render()
    
    def __init__(self, attrs=None, max_hours=24):
        super().__init__(attrs)
        self.max_hours = max_hours
    
    def render(self, name, value, attrs=None, renderer=None):
        # Parse the current value (timedelta or string)
        hours, minutes, seconds = 0, 0, 0
        
        if value:
            if isinstance(value, timedelta):
                total_seconds = int(value.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
            elif isinstance(value, str) and value:
                # Try to parse string formats like "HH:MM:SS" or just seconds
                try:
                    parts = value.split(':')
                    if len(parts) == 3:
                        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                    elif len(parts) == 2:
                        hours, minutes = 0, int(parts[0])
                        seconds = int(parts[1])
                    else:
                        # Assume it's just seconds
                        total_seconds = int(float(value))
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                except (ValueError, TypeError):
                    pass
        
        # Build the hours dropdown
        hours_options = ''.join(
            f'<option value="{h}"{" selected" if h == hours else ""}>{h:02d}</option>'
            for h in range(self.max_hours + 1)
        )
        
        # Build the minutes dropdown
        minutes_options = ''.join(
            f'<option value="{m}"{" selected" if m == minutes else ""}>{m:02d}</option>'
            for m in range(60)
        )
        
        # Build the seconds dropdown
        seconds_options = ''.join(
            f'<option value="{s}"{" selected" if s == seconds else ""}>{s:02d}</option>'
            for s in range(60)
        )
        
        html = f'''
        <div class="duration-dropdown-widget" style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <div style="display: flex; flex-direction: column; align-items: center;">
                <label style="font-size: 11px; color: #666; margin-bottom: 3px;">Hours</label>
                <select name="{name}_hours" id="id_{name}_hours" class="duration-dropdown" style="padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; min-width: 70px;">
                    {hours_options}
                </select>
            </div>
            <span style="font-size: 18px; font-weight: bold; margin-top: 18px;">:</span>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <label style="font-size: 11px; color: #666; margin-bottom: 3px;">Minutes</label>
                <select name="{name}_minutes" id="id_{name}_minutes" class="duration-dropdown" style="padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; min-width: 70px;">
                    {minutes_options}
                </select>
            </div>
            <span style="font-size: 18px; font-weight: bold; margin-top: 18px;">:</span>
            <div style="display: flex; flex-direction: column; align-items: center;">
                <label style="font-size: 11px; color: #666; margin-bottom: 3px;">Seconds</label>
                <select name="{name}_seconds" id="id_{name}_seconds" class="duration-dropdown" style="padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; min-width: 70px;">
                    {seconds_options}
                </select>
            </div>
        </div>
        '''
        return mark_safe(html)
    
    def value_from_datadict(self, data, files, name):
        """Convert the three dropdown values back to a timedelta-compatible string."""
        try:
            hours = int(data.get(f'{name}_hours', 0) or 0)
            minutes = int(data.get(f'{name}_minutes', 0) or 0)
            seconds = int(data.get(f'{name}_seconds', 0) or 0)
            
            # Return None if all values are 0 (no time limit)
            if hours == 0 and minutes == 0 and seconds == 0:
                return None
            
            # Return as HH:MM:SS format for DurationField to parse
            return f'{hours}:{minutes:02d}:{seconds:02d}'
        except (ValueError, TypeError):
            return None


class ContestParticipantUploadForm(forms.Form):
    participants_csv = forms.FileField(
        label=_('Upload Participants CSV/Excel'),
        help_text=_('CSV/Excel format: email in first column'),
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx', 'xls'])],
        required=False
    )

class HPEContestForm(ContestForm):
    participants_csv = forms.FileField(
        label=_('Upload Participants CSV/Excel'),
        help_text=mark_safe(_(
            'Upload a CSV or Excel file containing participant emails.<br>'
            '<small>Usernames will be automatically generated from emails if not provided.</small><br>'
            '<details>'
            '<summary><strong>View Example Format</strong></summary>'
            '<pre style="margin-top: 5px; background: #f5f5f5; padding: 5px; border-radius: 4px;">'
            '<strong>CSV or Excel - Email in first column</strong>\n'
            'john@example.com\n'
            'jane@example.com\n\n'
            '<strong>With optional username in second column</strong>\n'
            'john@example.com,john_doe\n'
            'jane@example.com,jane_smith'
            '</pre>'
            '</details>'
        )),
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx', 'xls'])],
        required=False
    )

    def __init__(self, *args, **kwargs):
        # Skip ContestForm.__init__ to avoid KeyErrors on missing fields (banned_users, etc.)
        # Call ModelForm.__init__ directly
        super(ContestForm, self).__init__(*args, **kwargs)
        
        # Apply custom duration dropdown widget for time_limit field
        if 'time_limit' in self.fields:
            self.fields['time_limit'].widget = DurationDropdownWidget(max_hours=48)
            self.fields['time_limit'].help_text = _('Select the contest duration using the dropdowns above. Leave all at 00 for no time limit.')
        
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
        
        # Rename 'group' to 'Difficulty'
        if 'group' in self.fields:
            self.fields['group'].label = _('Difficulty')
            self.fields['group'].help_text = _('Select difficulty level: Easy, Medium, or Hard')
            self.fields['group'].required = True

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
