import os
import io
import zipfile
from django.http import HttpResponse, FileResponse
from judge.models import ContestSubmission, SubmissionSource
import tempfile
import subprocess
import glob
import sys
from django.utils.text import slugify
from collections import defaultdict
from judge.models import ContestSubmission
from django_jinja import library


LANGUAGE_EXTENSIONS = {
    'C': 'c',
    'C++': 'cpp',
    'C++11': 'cpp',
    'Python 2': 'py',
    'Python 3': 'py',
    'Java': 'java',
    'Rust': 'rs',
    'Go': 'go',
    'Kotlin': 'kt',
    'Pascal': 'pas',
    'Ruby': 'rb',
    'Haskell': 'hs',
    'Perl': 'pl',
    'Scala': 'scala',
    'JavaScript': 'js',
}
def get_problem_languages_for_contest(contest):
    result = defaultdict(set)

    qs = ContestSubmission.objects.select_related(
        'submission__language', 'problem__problem', 'problem__contest'
    ).filter(problem__contest=contest)

    for entry in qs:
        code = entry.problem.problem.code
        lang = entry.submission.language.name
        result[code].add(lang)

    return dict(result)
    
@library.global_function
def problem_languages_for(contest):
    result = defaultdict(set)
    qs = ContestSubmission.objects.select_related(
        'submission__language', 'problem__problem', 'problem__contest'
    ).filter(problem__contest=contest)

    for entry in qs:
        code = entry.problem.problem.code
        lang = entry.submission.language.name
        result[code].add(lang)

    return dict(result)


def get_problem_languages(contest_key):
    mapping = defaultdict(set)

    qs = ContestSubmission.objects.select_related(
        'submission__language', 'problem__problem', 'problem__contest'
    ).filter(problem__contest__key=contest_key)

    for sub in qs:
        prob_code = sub.problem.problem.code
        lang = sub.submission.language.name
        mapping[prob_code].add(lang)

    return dict(mapping)

def build_submission_zip(problem_code, output_zip_path):
    submissions = ContestSubmission.objects.select_related(
        'submission', 'submission__language', 'submission__user',
        'problem__problem'
    ).filter(problem__problem__code=problem_code)

    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for contest_sub in submissions:
            submission = contest_sub.submission
            user = submission.user
            lang = submission.language.name
            ext = LANGUAGE_EXTENSIONS.get(lang, 'txt')
            username = user.username
            sub_id = submission.id

            filename = f"{username}_{sub_id}.{ext}"
            folder_path = f"{problem_code}/{lang}"
            full_path = f"{folder_path}/{filename}"

            try:
                source = SubmissionSource.objects.get(pk=submission.id)
                code = source.source
            except SubmissionSource.DoesNotExist:
                code = "// source not found"

            zipf.writestr(full_path, code)


def download_problem_submissions(request, contest_key, problem_code):
    submissions = ContestSubmission.objects.select_related(
        'submission', 'submission__language', 'submission__user',
        'problem__problem', 'problem__contest'
    ).filter(problem__problem__code=problem_code, problem__contest__key=contest_key)

    in_memory = io.BytesIO()

    with zipfile.ZipFile(in_memory, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for contest_sub in submissions:
            submission = contest_sub.submission
            user = submission.user
            lang = submission.language.name
            ext = LANGUAGE_EXTENSIONS.get(lang, 'txt')
            username = user.username
            sub_id = submission.id

            filename = f"{username}_{sub_id}.{ext}"
            folder_path = f"{problem_code}/{lang}"
            full_path = f"{folder_path}/{filename}"

            try:
                source = SubmissionSource.objects.get(pk=submission.id)
                code = source.source
            except SubmissionSource.DoesNotExist:
                code = "// source not found"

            zipf.writestr(full_path, code)

    in_memory.seek(0)
    response = HttpResponse(in_memory.read(), content_type="application/zip")
    response['Content-Disposition'] = f'attachment; filename="{problem_code}_submissions.zip"'
    return response

def download_problem_language_submissions(request, contest_key, problem_code, language):
    submissions = ContestSubmission.objects.select_related(
        'submission', 'submission__language', 'submission__user',
        'problem__problem', 'problem__contest'
    ).filter(
        problem__problem__code=problem_code,
        problem__contest__key=contest_key,
        submission__language__name=language
    )

    in_memory = io.BytesIO()

    with zipfile.ZipFile(in_memory, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for contest_sub in submissions:
            submission = contest_sub.submission
            user = submission.user
            lang = submission.language.name
            ext = LANGUAGE_EXTENSIONS.get(lang, 'txt')
            username = user.username
            sub_id = submission.id

            filename = f"{username}_{sub_id}.{ext}"
            full_path = f"{problem_code}/{filename}"  # No lang folder

            try:
                source = SubmissionSource.objects.get(pk=submission.id)
                code = source.source
            except SubmissionSource.DoesNotExist:
                code = "// source not found"

            zipf.writestr(full_path, code)

    in_memory.seek(0)
    filename = f"{problem_code}_{slugify(language)}_submissions.zip"
    response = HttpResponse(in_memory.read(), content_type="application/zip")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response





def normalize_language(lang):
    return lang.strip().lower().replace(' ', '').replace('+', 'p')

import os
import sys
import tempfile
import zipfile
import glob
import subprocess
from django.http import FileResponse

LANGUAGE_EXTENSIONS = {
    'C': 'c',
    'C++': 'cpp',
    'C++11': 'cpp',
    'Python 2': 'py',
    'Python 3': 'py',
    'Java': 'java',
    'Rust': 'rs',
    'Go': 'go',
    'Kotlin': 'kt',
    'Pascal': 'pas',
    'Ruby': 'rb',
    'Haskell': 'hs',
    'Perl': 'pl',
    'Scala': 'scala',
    'JavaScript': 'js',
}

def print_dir_tree(start_path):
    for root, dirs, files in os.walk(start_path):
        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}{f}")
    sys.stdout.flush()


import socket

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def download_and_analyze(request, contest_slug, problem_code, language):
    import sys
    import os
    import tempfile
    import zipfile
    import subprocess
    import glob
    import webbrowser
    import uuid
    import socket
    import time
    from django.http import FileResponse
    from django.shortcuts import redirect


    def get_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    print("==> download_and_analyze() called")
    sys.stdout.flush()

    print(f"Analyzing problem: {problem_code}, Language: {language}")
    sys.stdout.flush()

    tmp_dir = tempfile.mkdtemp()
    submissions_zip_path = os.path.join(tmp_dir, f"{problem_code}_submissions.zip")
    extract_dir = os.path.join(tmp_dir, "extracted")

    build_submission_zip(problem_code, submissions_zip_path)

    with zipfile.ZipFile(submissions_zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    print("Directory Tree After Extraction:")
    for root, dirs, files in os.walk(extract_dir):
        print(f"Dir: {root}")
        for file in files:
            print(f"  File: {file}")
    sys.stdout.flush()

    LANGUAGE_EXTENSIONS = {
        'C': 'c',
        'C++': 'cpp',
        'C++11': 'cpp',
        'Python 2': 'py',
        'Python 3': 'py',
        'Java': 'java',
        'Rust': 'rs',
        'Go': 'go',
        'Kotlin': 'kt',
        'Pascal': 'pas',
        'Ruby': 'rb',
        'Haskell': 'hs',
        'Perl': 'pl',
        'Scala': 'scala',
        'JavaScript': 'js',
    }

    DOLOS_LANGUAGE_NAMES = {
        'C': 'c',
        'C++': 'cpp',
        'C++11': 'cpp',
        'Python 2': 'python',
        'Python 3': 'python',
        'Java': 'java',
        'Rust': 'rust',
        'Go': 'go',
        'Kotlin': 'kotlin',
        'Pascal': 'pascal',
        'Ruby': 'ruby',
        'Haskell': 'haskell',
        'Perl': 'perl',
        'Scala': 'scala',
        'JavaScript': 'javascript',
    }

    ext = LANGUAGE_EXTENSIONS.get(language)
    dolos_lang = DOLOS_LANGUAGE_NAMES.get(language)

    if not ext or not dolos_lang:
        print(f"Unsupported language: {language}")
        sys.stdout.flush()
        return FileResponse(open(submissions_zip_path, 'rb'), as_attachment=True)

    # Find matching files
    candidates = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(f".{ext}"):
                candidates.append(os.path.join(root, file))

    print("Matched Files for Dolos:", candidates)
    sys.stdout.flush()

    if not candidates:
        print(f"No files found for language {language}")
    else:
        port = get_free_port()
        report_dir = os.path.join(tmp_dir, f"dolos_report_{uuid.uuid4().hex}")

        # 1. Generate the web report
        subprocess.run(
            ['dolos', 'run', '-f', 'web', '-o', report_dir, '-l', dolos_lang] + candidates,
            capture_output=True,
            text=True
        )

        # 2. Serve the report
        subprocess.Popen(['dolos', 'serve', '-p', str(port), report_dir])

        # 3. Open it in the browser
        url = f"http://localhost:{port}/"
        print(f"Opening {url}")
        webbrowser.open(url)

        # Optional: sleep to ensure server starts before view returns
        time.sleep(2)

    # return FileResponse(open(submissions_zip_path, 'rb'), as_attachment=True)
    url = f"http://localhost:{port}/"
    print(f"Opening {url}")
    sys.stdout.flush()

# Option 1: For automatic local dev browser open
    webbrowser.open(url)

# Option 2: For real user redirect
    return redirect(url)

