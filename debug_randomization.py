#!/usr/bin/env python
"""Debug script to check randomization config and participation data"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmoj.local_settings')
sys.path.insert(0, '/home/lalith/Desktop/Test_demoj_1/site')
django.setup()

from judge.models import Contest, ContestParticipation, ContestMCQ

# Get the most recent HPE contest
contest = Contest.objects.filter(key__startswith='hpe').order_by('-id').first()
if not contest:
    contest = Contest.objects.order_by('-id').first()

print(f"\n=== Contest: {contest.key} ===")
print(f"Randomize: {contest.randomize}")
print(f"Randomization Config: {contest.randomization_config}")

# Check MCQs and their groups
print(f"\n=== Contest MCQs ===")
for cm in contest.contest_mcqs.select_related('mcq_question', 'mcq_question__group').all():
    mcq = cm.mcq_question
    group_name = mcq.group.full_name if mcq.group else 'NO GROUP'
    print(f"  MCQ {mcq.id}: {mcq.code} - Group: {group_name}")

# Check participations
print(f"\n=== Participations ===")
for p in ContestParticipation.objects.filter(contest=contest):
    print(f"  User: {p.user.user.username}")
    print(f"    format_data: {p.format_data}")
    if p.format_data:
        print(f"    selected_problems: {p.format_data.get('selected_problems', 'NOT SET')}")
        print(f"    selected_mcqs: {p.format_data.get('selected_mcqs', 'NOT SET')}")
    print()
