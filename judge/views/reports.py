import os
import csv
import glob
import socket
import zipfile
import datetime
import subprocess
from collections import defaultdict

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from judge.models import Contest, ContestSubmission, ContestProblem, SubmissionSource


LANGUAGE_EXTENSIONS = {
    'C': 'c', 'C++': 'cpp', 'C++11': 'cpp', 'Python 2': 'py', 'Python 3': 'py',
    'Java': 'java', 'Rust': 'rs', 'Go': 'go', 'Kotlin': 'kt', 'Pascal': 'pas',
    'Ruby': 'rb', 'Haskell': 'hs', 'Perl': 'pl', 'Scala': 'scala', 'JavaScript': 'js',
}

DOLOS_LANGUAGE_FLAGS = {
    'C': 'c', 'C++': 'cpp', 'C++11': 'cpp', 'Python 2': 'python', 'Python 3': 'python',
    'Java': 'java', 'Rust': 'rs', 'Go': 'go', 'Kotlin': 'kt', 'Pascal': 'pas',
    'Ruby': 'rb', 'Haskell': 'hs', 'Perl': 'pl', 'Scala': 'scala', 'JavaScript': 'javascript',
}


def extract_username(filename):
    name = filename.rsplit('.', 1)[0]
    parts = name.split('_')
    if len(parts) >= 2 and parts[-1].isdigit():
        return '_'.join(parts[:-1])
    return name


def extract_similarity_data(report_dirs):
    similarity_data = defaultdict(lambda: defaultdict(float))

    for report_dir in report_dirs:
        similarities_csv = os.path.join(report_dir, "similarities.csv")
        if not os.path.isfile(similarities_csv):
            print(f"[!] similarities.csv not found in: {report_dir}")
            continue

        # Extract problem code from directory name
        problem_code = os.path.basename(report_dir)
        if "submissions" in problem_code:
            problem_code = problem_code.split("submissions")[0]
            problem_code = problem_code.split('-')[-1]

        with open(similarities_csv, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                file1 = os.path.basename(row['leftFilePath'])
                file2 = os.path.basename(row['rightFilePath'])
                similarity = float(row['similarity'])

                user1 = extract_username(file1)
                user2 = extract_username(file2)

                similarity_data[user1][problem_code] = max(similarity_data[user1][problem_code], similarity)
                similarity_data[user2][problem_code] = max(similarity_data[user2][problem_code], similarity)

    return similarity_data



def find_free_port(start_port=3001, max_port=3100, used_ports=set()):
    for port in range(start_port, max_port):
        if port in used_ports:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(('localhost', port)) != 0:
                used_ports.add(port)
                return port
    raise RuntimeError("No free port")


def run_dolos_and_generate_zip(contest_key, problem_code):
    base_dir = "/home/trishal/submissions"
    os.makedirs(base_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    tmp_dir = os.path.join(base_dir, f"contest_{contest_key}_{timestamp}")
    os.makedirs(tmp_dir, exist_ok=True)

    contest = Contest.objects.get(key=contest_key)
    problem = contest.problems.filter(code=problem_code).first()
    if not problem:
        return None, []

    submissions = ContestSubmission.objects.select_related(
        'submission', 'submission__language', 'submission__user'
    ).filter(
        problem__problem=problem,
        problem__contest=contest,
        submission__result='AC'
    )

    lang_buckets = {}
    for contest_sub in submissions:
        submission = contest_sub.submission
        user = submission.user
        lang = submission.language.name
        ext = LANGUAGE_EXTENSIONS.get(lang, 'txt')
        filename = f"{user.username}_{submission.id}.{ext}"

        try:
            source = SubmissionSource.objects.get(pk=submission.id)
            code = source.source
        except:
            continue

        lang_buckets.setdefault(lang, []).append((filename, code))

    used_ports = set()
    dolos_ports = []
    lang_zip_paths = []

    for lang, files in lang_buckets.items():
        zip_filename = f"{problem_code}_{lang.replace(' ', '_')}_submissions.zip"
        zip_path = os.path.join(tmp_dir, zip_filename)
        lang_zip_paths.append(zip_path)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename, code in files:
                zipf.writestr(filename, code)

        lang_flag = DOLOS_LANGUAGE_FLAGS.get(lang)
        if lang_flag:
            csv_output_dir = f"dolos-report-{timestamp}-{problem_code}{lang.replace(' ', '')}submissions"
            csv_output_path = os.path.join(tmp_dir, csv_output_dir)

            subprocess.run([
                "dolos", "run", "-f", "csv", "-l", lang_flag,
                zip_path, "-o", csv_output_path
            ], cwd=tmp_dir)


            try:
                port = find_free_port(3001, 3100, used_ports)
                subprocess.Popen([
                    "dolos", "run", "-f", "web", "-l", lang_flag,
                    "--port", str(port), zip_path
                ], cwd=tmp_dir)
                dolos_ports.append(port)
            except Exception as e:
                print(f"[!] Failed to launch Dolos web: {e}")
        else:
            print(f"[!] Missing language flag for: {lang}")

    report_dirs = glob.glob(os.path.join(tmp_dir, "dolos-report-*"))
    sim_data = extract_similarity_data(report_dirs)

    matrix_path = os.path.join(tmp_dir, f"{contest_key}_similarity_matrix.txt")
    with open(matrix_path, 'w') as f:
        for username, scores in sim_data.items():
            line = f"{username}"
            for problem_key, val in scores.items():
                line += f" : {problem_key} {val:.2f}%"
            f.write(line + "\n")

    final_zip_path = os.path.join(tmp_dir, f"{contest_key}_grouped_submissions.zip")
    with zipfile.ZipFile(final_zip_path, 'w') as final_zip:
        for zip_file in lang_zip_paths:
            final_zip.write(zip_file, arcname=os.path.basename(zip_file))
        final_zip.write(matrix_path, arcname=os.path.basename(matrix_path))

    return final_zip_path, dolos_ports


# View to trigger the plagiarism report generation
def generate_plagiarism_report(request, contest_key, problem_id):
    problem = get_object_or_404(ContestProblem, id=problem_id)

    zip_path, dolos_ports = run_dolos_and_generate_zip(contest_key, problem.problem.code)
    request.session['plagiarism_zip_path'] = zip_path

    if request.GET.get('mode') == 'download':
        return FileResponse(open(zip_path, 'rb'), as_attachment=True, filename=os.path.basename(zip_path))

    return render(request, 'contest/plagiarism_report_redirect.html', {
        'title': 'Generating Plagiarism Report',
        'zip_url': request.path + '?mode=download',
        'dolos_ports': dolos_ports
    })


# View to list all problems and link to their report generation
def plagiarism_report_page(request, contest_key):
    contest = get_object_or_404(Contest, key=contest_key)
    problems = ContestProblem.objects.filter(contest=contest).select_related('problem')

    reports = [{
        'problem_name': problem.problem.name,
        'problem_id': problem.id,
        'problem_code': problem.problem.code,
        'url': reverse('generate_plagiarism_report', kwargs={
            'contest_key': contest_key,
            'problem_id': problem.id
        })
    } for problem in problems]

    return render(request, 'contest/plagiarism_report_page.html', {
        'reports': reports,
        'contest_key': contest_key,
    })
