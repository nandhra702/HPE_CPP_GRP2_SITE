from django.http import FileResponse
import tempfile
import os
import zipfile
import subprocess
import csv
from collections import defaultdict
import socket
from judge.models import Contest, ContestSubmission, SubmissionSource
import datetime
import glob
from django.shortcuts import render

timestamp = datetime.datetime.now().strftime('%Y_%m_%d___%H_%M_%S')
report_csv_paths = []


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
   
    name = filename.rsplit('.', 1)[0]  # Remove extension
    parts = name.split('_')
    if len(parts) >= 2 and parts[-1].isdigit():
        return '_'.join(parts[:-1])  # Remove submission ID
    return name  # fallback (e.g. no underscore or submission ID)



def extract_similarity_data(report_csv_paths):
    similarity_data = defaultdict(lambda: defaultdict(float))  # username -> problem_code -> max_similarity

    for path in report_csv_paths:
        if not os.path.exists(path):
            print(f"[!] Missing Dolos output: {path}")

        # Extract problem code from directory name instead of filename
        parent_dir = os.path.basename(os.path.dirname(path))  # e.g. dolos-report-*-twosumPython3submissions
        problem_code = parent_dir.split('-')[-1]  # Extracts 'twosumPython3submissions'
        
        # Optional cleanup: remove 'submissions' suffix
        if problem_code.endswith('submissions'):
            problem_code = problem_code[:-11]  # now just 'twosumPython3'


        with open(path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                file1 = os.path.basename(row['leftFilePath'])   # e.g. personal_sukhraj_45.py
                file2 = os.path.basename(row['rightFilePath'])  # e.g. sukhraj_47.py
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
    raise RuntimeError("No free port found in range.")

    # ///////////////////////////////////

def download_problem_submissions(request, contest_key):
    contest = Contest.objects.get(key=contest_key)
    problems = contest.problems.all()
    base_dir = "/home/sukhraj/submissions"  # or any path you want
    os.makedirs(base_dir, exist_ok=True)
    tmp_dir = os.path.join(base_dir, f"contest_{contest_key}_{timestamp}")
    os.makedirs(tmp_dir, exist_ok=True)

    lang_zip_paths = []
    used_ports = set()

    try:
        for problem in problems:
            problem_code = problem.code

            submissions = ContestSubmission.objects.select_related(
                'submission', 'submission__language', 'submission__user',
                'problem__problem', 'problem__contest'
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
                username = user.username
                sub_id = submission.id

                filename = f"{username}_{sub_id}.{ext}"

                try:
                    source = SubmissionSource.objects.get(pk=submission.id)
                    code = source.source
                except SubmissionSource.DoesNotExist:
                    print(f"[!] Source missing for submission ID: {submission.id}")
                    continue

                lang_buckets.setdefault(lang, []).append((filename, code))

            for lang, files in lang_buckets.items():
                zip_filename = f"{problem_code}_{lang.replace(' ', '_')}_submissions.zip"
                zip_path = os.path.join(tmp_dir, zip_filename)
                lang_zip_paths.append(zip_path)

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for filename, code in files:
                        zipf.writestr(filename, code)

                lang_flag = DOLOS_LANGUAGE_FLAGS.get(lang, None)
                if lang_flag:
                    try:
                        free_port = find_free_port(start_port=3001, used_ports=used_ports)
                        subprocess.Popen([
                            "dolos", "run", "-f", "web", "-l", lang_flag,
                            "--port", str(free_port), zip_path],cwd=tmp_dir)

                        csv_output_path = zip_path.replace(".zip", "_report.csv")
                        with open(csv_output_path, 'w') as csv_file:
                            subprocess.run([
                                "dolos", "run", "-f", "csv", "-l", lang_flag,
                                zip_path], stdout=csv_file, cwd=tmp_dir)    
                    except Exception as e:
                        print(f"[✗] Dolos failed for {zip_filename}: {e}")
                else:
                    print(f"[!] Skipping Dolos: No language flag for '{lang}'")

      

        report_csv_paths = glob.glob(os.path.join(tmp_dir, "dolos-report-*/pairs.csv"))

        sim_data = extract_similarity_data(report_csv_paths)

        similarity_matrix_path = os.path.join(tmp_dir, f"{contest_key}_similarity_matrix.txt")
        with open(similarity_matrix_path, 'w') as out_file:
            for username, scores in sim_data.items():
                line = f"{username}"
                for problem in problems:
                    code = problem.code

                    # Try to find any key in scores that contains the problem code
                    matching_key = next((k for k in scores if code in k), None)
                    sim_percent = (scores[matching_key]*100) if matching_key else 0.0

                    line += f" : {code} {sim_percent:.2f}%"
                out_file.write(line + "\n")
        
        final_zip_path = os.path.join(tmp_dir, f"{contest_key}_grouped_submissions.zip")
        with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as final_zip:
            for zip_file in lang_zip_paths:
                arcname = os.path.basename(zip_file)
                final_zip.write(zip_file, arcname=arcname)



            final_zip.write(similarity_matrix_path, arcname=os.path.basename(similarity_matrix_path))



        return FileResponse(open(final_zip_path, 'rb'), as_attachment=True,
                            filename=f"{contest_key}_grouped_submissions.zip")

    finally:
        print("[✓] Finished preparing submissions and running Dolos.")


#CREATING THE TABLE TO BE DISPLAYED


def read_similarity_matrix(contest_key):
    pattern = f"/home/sukhraj/submissions/contest_{contest_key}_*/{contest_key}_similarity_matrix.txt"
    matching_files = glob.glob(pattern)
    if not matching_files:
        return [], []

    # Optional: pick the most recent one
    path = max(matching_files, key=os.path.getmtime)

    with open(path, 'r') as file:
        lines = file.readlines()

    headers = []
    rows = []

    for line in lines:
        parts = line.strip().split(':')
        username = parts[0].strip()
        entries = parts[1:]

        row = [username]
        for entry in entries:
            pieces = entry.strip().split()
            if len(pieces) == 2:
                question, score = pieces
                row.append(score)
                if len(headers) < len(entries):
                    headers.append(question)

        rows.append(row)

    return headers, rows

#NOW SHOW THE TABLE

def show_similarity_table(request, contest_key):
    headers, rows = read_similarity_matrix(contest_key)
    return render(request, 'contest/show_similarity_table.html', {
        'headers': headers,
        'rows': rows,
    })
