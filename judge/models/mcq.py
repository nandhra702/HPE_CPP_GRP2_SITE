from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import CASCADE, SET_NULL, Max
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property

from judge.models.profile import Organization, Profile
from judge.models.problem import ProblemGroup, ProblemType, License, disallowed_characters_validator
from operator import attrgetter
from judge.user_translations import gettext as user_gettext

__all__ = ['MCQQuestion', 'MCQOption', 'MCQSubmission']


class MCQQuestion(models.Model):
    """
    Model for Multiple Choice Questions
    """
    QUESTION_TYPE_CHOICES = (
        ('SINGLE', _('Single Choice')),
        ('MULTIPLE', _('Multiple Choice')),
    )

    code = models.CharField(
        max_length=20,
        verbose_name=_('question code'),
        unique=True,
        validators=[RegexValidator('^[a-z0-9]+$', _('Question code must be ^[a-z0-9]+$'))],
        help_text=_('A short, unique code for the question, used in the URL after /mcq/')
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_('question title'),
        db_index=True,
        help_text=_('The title/summary of the question'),
        validators=[disallowed_characters_validator]
    )
    description = models.TextField(
        verbose_name=_('question text'),
        help_text=_('The full question text, supports markdown'),
        validators=[disallowed_characters_validator]
    )
    question_type = models.CharField(
        max_length=10,
        verbose_name=_('format'),
        choices=QUESTION_TYPE_CHOICES,
        default='SINGLE',
        help_text=_('Format of MCQ question')
    )
    points = models.FloatField(
        verbose_name=_('points'),
        help_text=_('Points awarded for correct answer'),
        validators=[MinValueValidator(0.1)],
        default=1.0
    )
    partial_credit = models.BooleanField(
        verbose_name=_('allow partial credit'),
        default=False,
        help_text=_('For multiple choice questions, award partial points for partially correct answers')
    )
    explanation = models.TextField(
        verbose_name=_('explanation'),
        blank=True,
        help_text=_('Explanation shown after answering (optional)'),
        validators=[disallowed_characters_validator]
    )
    
    # Categorization
    types = models.ManyToManyField(
        ProblemType,
        verbose_name=_('question types'),
        help_text=_("The type of question, similar to problem types"),
        blank=True
    )
    group = models.ForeignKey(
        ProblemGroup,
        verbose_name=_('question group'),
        on_delete=CASCADE,
        help_text=_('The group/category of question'),
        null=True,
        blank=True
    )
    
    # Access control
    authors = models.ManyToManyField(
        Profile,
        verbose_name=_('creators'),
        blank=True,
        related_name='authored_mcqs',
        help_text=_('Users who can edit this question')
    )
    curators = models.ManyToManyField(
        Profile,
        verbose_name=_('curators'),
        blank=True,
        related_name='curated_mcqs',
        help_text=_('Users who can edit but are not listed as authors')
    )
    is_public = models.BooleanField(
        verbose_name=_('publicly visible'),
        db_index=True,
        default=False
    )
    date = models.DateTimeField(
        verbose_name=_('date of publishing'),
        null=True,
        blank=True,
        db_index=True
    )
    
    organizations = models.ManyToManyField(
        Organization,
        blank=True,
        verbose_name=_('organizations'),
        help_text=_('If private, only these organizations may see the question')
    )
    is_organization_private = models.BooleanField(
        verbose_name=_('private to organizations'),
        default=False
    )
    
    license = models.ForeignKey(
        License,
        null=True,
        blank=True,
        on_delete=SET_NULL,
        verbose_name=_('license')
    )
    
    # Statistics
    user_count = models.IntegerField(
        verbose_name=_('number of users'),
        default=0,
        help_text=_('Number of users who answered correctly')
    )
    ac_rate = models.FloatField(
        verbose_name=_('accuracy rate'),
        default=0
    )
    
    # Options display
    randomize_options = models.BooleanField(
        verbose_name=_('randomize option order'),
        default=True,
        editable=False,
        help_text=_('Randomize the order of options for each user')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @cached_property
    def types_list(self):
        return list(map(user_gettext, map(attrgetter('full_name'), self.types.all())))

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_absolute_url(self):
        # URL pattern not yet implemented, return admin URL for now
        from django.urls import reverse
        try:
            return reverse('admin:judge_mcqquestion_change', args=(self.pk,))
        except:
            return '#'

    def is_editor(self, profile):
        return (self.authors.filter(id=profile.id) | self.curators.filter(id=profile.id)).exists()

    def is_editable_by(self, user):
        if not user.is_authenticated:
            return False
        if not user.has_perm('judge.edit_own_mcq'):
            return False
        if user.has_perm('judge.edit_all_mcq'):
            return True
        if user.profile in self.authors.all() or user.profile in self.curators.all():
            return True
        if self.is_organization_private and self.organizations.filter(admins=user.profile).exists():
            return True
        return False

    class Meta:
        verbose_name = _('MCQ question')
        verbose_name_plural = _('MCQ questions')
        ordering = ['code']
        permissions = (
            ('edit_own_mcq', _('Edit own MCQ questions')),
            ('edit_all_mcq', _('Edit all MCQ questions')),
        )


class MCQOption(models.Model):
    """
    Model for MCQ answer options
    """
    question = models.ForeignKey(
        MCQQuestion,
        on_delete=CASCADE,
        related_name='options',
        verbose_name=_('question')
    )
    option_text = models.TextField(
        verbose_name=_('option text'),
        help_text=_('The text for this answer option, supports markdown')
    )
    is_correct = models.BooleanField(
        verbose_name=_('is correct answer'),
        default=False,
        help_text=_('Check if this is a correct answer')
    )
    order = models.PositiveIntegerField(
        verbose_name=_('display order'),
        default=0,
        help_text=_('Order in which option appears (0-based, ignored if randomize is enabled)')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.question.code} - Option {self.order + 1}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            # Auto-assign sequential order whenever new options are added and the requested slot is taken
            if MCQOption.objects.filter(question=self.question, order=self.order).exists():
                max_order = MCQOption.objects.filter(question=self.question).aggregate(
                    max_order=Max('order')
                )['max_order']
                self.order = (max_order or -1) + 1
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('MCQ option')
        verbose_name_plural = _('MCQ options')
        ordering = ['question', 'order']
        unique_together = [['question', 'order']]

    def clean(self):
        pass


class MCQSubmission(models.Model):
    """
    Model for tracking MCQ submissions
    """
    question = models.ForeignKey(
        MCQQuestion,
        on_delete=CASCADE,
        related_name='submissions',
        verbose_name=_('question')
    )
    user = models.ForeignKey(
        Profile,
        on_delete=CASCADE,
        related_name='mcq_submissions',
        verbose_name=_('user')
    )
    selected_options = models.ManyToManyField(
        MCQOption,
        verbose_name=_('selected options'),
        help_text=_('Options selected by the user')
    )
    is_correct = models.BooleanField(
        verbose_name=_('is correct'),
        default=False
    )
    points_earned = models.FloatField(
        verbose_name=_('points earned'),
        default=0.0
    )
    time_taken = models.PositiveIntegerField(
        verbose_name=_('time taken (seconds)'),
        null=True,
        blank=True,
        help_text=_('Time taken to answer in seconds')
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('submission time')
    )
    contest_object = models.ForeignKey(
        'ContestMCQ',
        verbose_name=_('contest MCQ'),
        null=True,
        blank=True,
        on_delete=CASCADE,
        related_name='submissions',
        help_text=_('Contest MCQ this submission belongs to (if in contest)')
    )
    participation = models.ForeignKey(
        'ContestParticipation',
        verbose_name=_('contest participation'),
        null=True,
        blank=True,
        on_delete=CASCADE,
        related_name='mcq_submissions',
        help_text=_('Contest participation this submission belongs to (if in contest)')
    )

    def __str__(self):
        return f"{self.user.user.username} - {self.question.code}"

    class Meta:
        verbose_name = _('MCQ submission')
        verbose_name_plural = _('MCQ submissions')
        ordering = ['-submitted_at']
        # Allow multiple submissions per user per question if different contests
        # but only one submission per user per question outside contests

    def calculate_score(self):
        """
        Calculate the score based on selected options
        """
        correct_options = set(self.question.options.filter(is_correct=True))
        selected = set(self.selected_options.all())
        
        if self.question.question_type == 'SINGLE':
            # For single choice, must select exactly the correct option
            if selected == correct_options and len(selected) == 1:
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0.0
        
        elif self.question.question_type == 'MULTIPLE':
            # For multiple choice
            if selected == correct_options:
                self.is_correct = True
                self.points_earned = self.question.points
            elif self.question.partial_credit and selected:
                # Partial credit calculation
                correct_selected = len(selected & correct_options)
                incorrect_selected = len(selected - correct_options)
                total_correct = len(correct_options)
                
                # Award partial points: (correct - incorrect) / total_correct
                if correct_selected > incorrect_selected:
                    ratio = (correct_selected - incorrect_selected) / total_correct
                    self.points_earned = max(0, self.question.points * ratio)
                else:
                    self.points_earned = 0.0
                self.is_correct = False
            else:
                self.is_correct = False
                self.points_earned = 0.0
        
        self.save()
