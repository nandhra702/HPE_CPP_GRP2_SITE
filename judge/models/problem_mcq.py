"""
Multiple Choice Question (MCQ) support for DMOJ
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import json

__all__ = ['MCQQuestion', 'MCQOption', 'MCQSubmission']


class MCQQuestion(models.Model):
    """
    Model for storing MCQ-specific data for a problem.
    A problem can have multiple MCQ questions.
    """
    problem = models.ForeignKey('Problem', verbose_name=_('problem'), 
                                related_name='mcq_questions', on_delete=models.CASCADE)
    order = models.IntegerField(verbose_name=_('question order'), 
                                help_text=_('Order in which the question appears in the problem'))
    question_text = models.TextField(verbose_name=_('question text'),
                                      help_text=_('The MCQ question text'))
    explanation = models.TextField(verbose_name=_('explanation'), blank=True,
                                    help_text=_('Explanation shown after answering (optional)'))
    points = models.FloatField(verbose_name=_('points'), default=1.0,
                               validators=[MinValueValidator(0.0)],
                               help_text=_('Points awarded for correct answer'))
    allow_multiple = models.BooleanField(verbose_name=_('allow multiple answers'), default=False,
                                         help_text=_('Whether multiple options can be selected'))
    
    class Meta:
        ordering = ['problem', 'order']
        verbose_name = _('MCQ question')
        verbose_name_plural = _('MCQ questions')
        unique_together = ('problem', 'order')
    
    def __str__(self):
        return f'MCQ {self.order} for {self.problem.code}'
    
    def clean(self):
        # Validate that at least one correct answer exists
        if self.pk:
            correct_count = self.options.filter(is_correct=True).count()
            if correct_count == 0:
                raise ValidationError(_('At least one option must be marked as correct'))
            if not self.allow_multiple and correct_count > 1:
                raise ValidationError(_('Only one option can be correct when multiple answers are not allowed'))
    
    def get_correct_options(self):
        """Returns queryset of correct options"""
        return self.options.filter(is_correct=True)
    
    def check_answer(self, selected_option_ids):
        """
        Check if the submitted answer is correct.
        
        Args:
            selected_option_ids: List of selected option IDs
            
        Returns:
            tuple: (is_correct, points_earned)
        """
        if not isinstance(selected_option_ids, list):
            selected_option_ids = [selected_option_ids]
        
        correct_option_ids = set(self.get_correct_options().values_list('id', flat=True))
        selected_option_ids = set(selected_option_ids)
        
        if correct_option_ids == selected_option_ids:
            return True, self.points
        else:
            return False, 0.0


class MCQOption(models.Model):
    """
    Model for storing individual options for an MCQ question.
    """
    question = models.ForeignKey(MCQQuestion, verbose_name=_('question'),
                                 related_name='options', on_delete=models.CASCADE)
    order = models.IntegerField(verbose_name=_('option order'),
                                help_text=_('Order in which the option appears'))
    option_text = models.CharField(max_length=500, verbose_name=_('option text'),
                                    help_text=_('The text of this option'))
    is_correct = models.BooleanField(verbose_name=_('is correct'), default=False,
                                      help_text=_('Whether this option is a correct answer'))
    
    class Meta:
        ordering = ['question', 'order']
        verbose_name = _('MCQ option')
        verbose_name_plural = _('MCQ options')
        unique_together = ('question', 'order')
    
    def __str__(self):
        return f'Option {self.order}: {self.option_text[:50]}'


class MCQSubmission(models.Model):
    """
    Model for storing MCQ submission answers.
    Links to the main Submission model.
    """
    submission = models.OneToOneField('Submission', verbose_name=_('submission'),
                                      related_name='mcq_submission', on_delete=models.CASCADE)
    answers = models.JSONField(verbose_name=_('MCQ answers'),
                               help_text=_('JSON storing question_id -> selected_option_ids mapping'))
    
    class Meta:
        verbose_name = _('MCQ submission')
        verbose_name_plural = _('MCQ submissions')
    
    def __str__(self):
        return f'MCQ answers for submission {self.submission.id}'
    
    def get_answers_dict(self):
        """Returns the answers as a Python dictionary"""
        if isinstance(self.answers, str):
            return json.loads(self.answers)
        return self.answers
    
    def set_answers_dict(self, answers_dict):
        """Sets the answers from a Python dictionary"""
        self.answers = answers_dict
    
    def calculate_score(self):
        """
        Calculate the total score for this MCQ submission.
        
        Returns:
            tuple: (total_points_earned, total_points_possible, details)
        """
        answers_dict = self.get_answers_dict()
        total_earned = 0.0
        total_possible = 0.0
        details = []
        
        # Get all questions for this problem
        problem = self.submission.problem
        questions = problem.mcq_questions.all()
        
        for question in questions:
            total_possible += question.points
            question_id_str = str(question.id)
            
            if question_id_str in answers_dict:
                selected_ids = answers_dict[question_id_str]
                is_correct, points = question.check_answer(selected_ids)
                total_earned += points
                details.append({
                    'question_id': question.id,
                    'correct': is_correct,
                    'points_earned': points,
                    'points_possible': question.points,
                })
            else:
                # Question not answered
                details.append({
                    'question_id': question.id,
                    'correct': False,
                    'points_earned': 0.0,
                    'points_possible': question.points,
                })
        
        return total_earned, total_possible, details
