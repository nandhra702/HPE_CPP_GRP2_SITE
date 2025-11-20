from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import ModelForm
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext, gettext_lazy as _, ngettext
from reversion.admin import VersionAdmin

from judge.models import MCQQuestion, MCQOption, MCQSubmission, Profile
from judge.models.problem import ProblemGroup
from judge.utils.views import NoBatchDeleteMixin
from judge.widgets import AdminHeavySelect2MultipleWidget, AdminMartorWidget, AdminSelect2MultipleWidget, \
    AdminSelect2Widget


class MCQQuestionForm(ModelForm):
    change_message = forms.CharField(max_length=256, label=_('Edit reason'), required=False)

    def __init__(self, *args, **kwargs):
        super(MCQQuestionForm, self).__init__(*args, **kwargs)
        self.fields['authors'].widget.can_add_related = False
        self.fields['curators'].widget.can_add_related = False
        self.fields['change_message'].widget.attrs.update({
            'placeholder': gettext('Describe the changes you made (optional)'),
        })

    class Meta:
        exclude = ('randomize_options',)
        widgets = {
            'authors': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'curators': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'organizations': AdminHeavySelect2MultipleWidget(data_view='organization_select2'),
            'types': AdminSelect2MultipleWidget,
            'group': AdminSelect2Widget,
            'description': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('problem_preview')}),
            'explanation': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('problem_preview')}),
        }


class MCQOptionInlineForm(ModelForm):
    class Meta:
        model = MCQOption
        fields = ('option_text', 'is_correct')
        widgets = {
            'option_text': forms.Textarea(attrs={'rows': 3, 'cols': 80}),
        }


class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    form = MCQOptionInlineForm
    fields = ('option_text', 'is_correct')
    extra = 4
    min_num = 2
    max_num = 10
    validate_min = True

    def get_formset(self, request, obj=None, **kwargs):
        formset_class = super().get_formset(request, obj, **kwargs)
        
        # Add custom validation to the formset
        original_clean = formset_class.clean
        
        def clean_with_validation(formset_self):
            if original_clean:
                original_clean(formset_self)
            
            if not obj:
                return
                
            # Count correct answers from the formset
            correct_count = 0
            for form in formset_self.forms:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    if form.cleaned_data.get('is_correct', False):
                        correct_count += 1
            
            # Validate based on question type
            if obj.question_type == 'SINGLE':
                if correct_count > 1:
                    raise ValidationError(
                        _('Single choice questions can only have ONE correct answer. You have marked %(count)d options as correct.'),
                        params={'count': correct_count}
                    )
                elif correct_count == 0:
                    raise ValidationError(
                        _('Single choice questions must have exactly one correct answer.')
                    )
            elif obj.question_type == 'MULTIPLE':
                if correct_count < 1:
                    raise ValidationError(
                        _('Multiple choice questions must have at least one correct answer.')
                    )
        
        formset_class.clean = clean_with_validation
        return formset_class


class MCQCreatorListFilter(admin.SimpleListFilter):
    title = parameter_name = 'creator'

    def lookups(self, request, model_admin):
        queryset = Profile.objects.exclude(authored_mcqs=None).values_list('user__username', flat=True)
        return [(name, name) for name in queryset]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(authors__user__username=self.value())


class MCQQuestionAdmin(NoBatchDeleteMixin, VersionAdmin):
    fieldsets = (
        (None, {
            'fields': (
                'code', 'name', 'question_type', 'is_public', 'date',
                'authors', 'curators', 'organizations', 'description',
            ),
        }),
        (_('Settings'), {
            'fields': ('points', 'partial_credit', 'explanation', 'license'),
        }),
        (_('Taxonomy'), {'fields': ('types', 'group')}),
        (_('History'), {'fields': ('change_message',)}),
    )
    list_display = ['code', 'name', 'question_type', 'show_authors', 'points', 'is_public']
    ordering = ['code']
    search_fields = ('code', 'name', 'authors__user__username', 'curators__user__username')
    inlines = [MCQOptionInline]
    list_max_show_all = 1000
    actions_on_top = True
    actions_on_bottom = True
    list_filter = ('is_public', 'question_type', MCQCreatorListFilter)
    form = MCQQuestionForm
    date_hierarchy = 'date'

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not request.user.has_perm('judge.edit_all_mcq'):
            if obj and not obj.is_editable_by(request.user):
                # Make most fields readonly if user can't edit
                return fields + ('code', 'question_type', 'organizations', 'is_public')
        return fields

    @admin.display(description=_('authors'))
    def show_authors(self, obj):
        authors = obj.authors.all()
        if authors:
            return ', '.join([author.user.username for author in authors])
        return '-'

    @admin.display(description=_('Mark questions as public'))
    def make_public(self, request, queryset):
        count = queryset.update(is_public=True)
        self.message_user(request, ngettext(
            '%d question successfully marked as public.',
            '%d questions successfully marked as public.',
            count) % count)

    @admin.display(description=_('Mark questions as private'))
    def make_private(self, request, queryset):
        count = queryset.update(is_public=False)
        self.message_user(request, ngettext(
            '%d question successfully marked as private.',
            '%d questions successfully marked as private.',
            count) % count)

    def get_actions(self, request):
        actions = super(MCQQuestionAdmin, self).get_actions(request)
        
        if request.user.has_perm('judge.edit_all_mcq'):
            func, name, desc = self.get_action('make_public')
            actions[name] = (func, name, desc)
            
            func, name, desc = self.get_action('make_private')
            actions[name] = (func, name, desc)
        
        return actions

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.has_perm('judge.edit_all_mcq'):
            return queryset.prefetch_related('authors__user', 'options').distinct()
        # Filter to only show questions user can edit
        return queryset.filter(
            models.Q(authors__user=request.user) |
            models.Q(curators__user=request.user) |
            models.Q(organizations__admins__user=request.user)
        ).prefetch_related('authors__user', 'options').distinct()

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return request.user.has_perm('judge.edit_own_mcq')
        return obj.is_editable_by(request.user)

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return request.user.has_perm('judge.edit_own_mcq')
        return obj.is_editable_by(request.user)

    def save_model(self, request, obj, form, change):
        # Handle organization privacy
        if form.changed_data and 'organizations' in form.changed_data:
            obj.is_organization_private = bool(form.cleaned_data['organizations'])
        obj.randomize_options = True
        if obj.group is None:
            obj.group, _created = ProblemGroup.objects.get_or_create(
                name='uncategorized',
                defaults={'full_name': _('Uncategorized')}
            )
        
        super(MCQQuestionAdmin, self).save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """Save MCQ options with auto-assigned order values"""
        if formset.model == MCQOption:
            instances = formset.save(commit=False)

            # Ensure options have unique sequential order values even though the field is hidden
            existing_orders = MCQOption.objects.filter(question=form.instance).exclude(
                pk__in=[instance.pk for instance in instances if instance.pk]
            ).values_list('order', flat=True)
            used_orders = set(existing_orders)
            next_order = 0

            for instance in instances:
                if instance.order is None or instance.order in used_orders or instance.pk is None:
                    while next_order in used_orders:
                        next_order += 1
                    instance.order = next_order
                    used_orders.add(next_order)
                    next_order += 1
            
            for instance in instances:
                instance.save()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)

    def construct_change_message(self, request, form, *args, **kwargs):
        if form.cleaned_data.get('change_message'):
            return form.cleaned_data['change_message']
        return super(MCQQuestionAdmin, self).construct_change_message(request, form, *args, **kwargs)


class MCQSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'question_display', 'is_correct', 'points_earned', 'time_taken', 'submitted_at')
    list_filter = ('is_correct', 'submitted_at')
    search_fields = ('user__user__username', 'question__code', 'question__name')
    readonly_fields = ('question', 'user', 'selected_options', 'is_correct', 'points_earned', 'time_taken', 'submitted_at')
    filter_horizontal = ('selected_options',)

    @admin.display(description=_('user'), ordering='user__user__username')
    def user_display(self, obj):
        return obj.user.user.username

    @admin.display(description=_('question'), ordering='question__code')
    def question_display(self, obj):
        return f"{obj.question.code} - {obj.question.name}"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion if user has permission
        return request.user.has_perm('judge.delete_mcqsubmission')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.has_perm('judge.edit_all_mcq'):
            return queryset.select_related('user__user', 'question')
        # Show only submissions for questions user can edit
        return queryset.filter(
            models.Q(question__authors__user=request.user) |
            models.Q(question__curators__user=request.user)
        ).select_related('user__user', 'question').distinct()


# Import models for the queryset filtering
from django.db import models
