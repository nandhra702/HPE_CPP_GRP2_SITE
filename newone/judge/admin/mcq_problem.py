from django.contrib import admin
from judge.models import MCQProblem, MCQOption

class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 2


@admin.register(MCQProblem)
class MCQProblemAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'question_text', 'is_public'),
        }),
    )
    list_display = ('code', 'name', 'is_public')
    inlines = [MCQOptionInline]
