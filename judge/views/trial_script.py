from django.http import FileResponse, HttpResponseNotFound
import tempfile
import os
import zipfile
import subprocess
import csv
from collections import defaultdict
import socket
import datetime
import glob

from judge.models import Contest, ContestSubmission, SubmissionSource

timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

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

        # Extract problem code
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
    raise RuntimeError("No free port found in range.")


def download_problem_submissions(request, contest_key, problem_code):
    contest = Contest.objects.get(key=contest_key)
    problem = contest.problems.filter(code=problem_code).first()
    if not problem:
        return HttpResponseNotFound("Problem not found in this contest.")
    problems = [problem]

    base_dir = "/home/trishal/submissions"
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
                filename = f"{user.username}_{submission.id}.{ext}"

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

                lang_flag = DOLOS_LANGUAGE_FLAGS.get(lang)
                if lang_flag:
                    try:
                        free_port = find_free_port(start_port=3001, used_ports=used_ports)
                        subprocess.Popen([
                            "dolos", "run", "-f", "web", "-l", lang_flag,
                            "--port", str(free_port), zip_path
                        ], cwd=tmp_dir)

                        csv_output_dir = f"dolos-report-{timestamp}-{problem_code}{lang.replace(' ', '')}submissions"
                        csv_output_path = os.path.join(tmp_dir, csv_output_dir)

                        with open(csv_output_path, 'w') as csv_file:
                            ssubprocess.run([
                                "dolos", "run", "-f", "csv", "-l", lang_flag,
                                zip_path, "-o", csv_output_path
                        ], cwd=tmp_dir)
                    except Exception as e:
                        print(f"[✗] Dolos failed for {zip_filename}: {e}")
                else:
                    print(f"[!] Skipping Dolos: No language flag for '{lang}'")

        report_dirs = glob.glob(os.path.join(tmp_dir, "dolos-report-*"))
        sim_data = extract_similarity_data(report_dirs)

        print("Final similarity data:", sim_data)
        print("[Debug] Extracted Similarity Data:")
        for user, scores in sim_data.items():
            print(f"  {user} -> {scores}")


        similarity_matrix_path = os.path.join(tmp_dir, f"{contest_key}_similarity_matrix.txt")
        with open(similarity_matrix_path, 'w') as out_file:
            for username, scores in sim_data.items():
                line = f"{username}"
                
                for problem in problems:

                    code = problem.code
                    matching_key = next((k for k in scores if code in k), None)
                    sim_percent = scores[matching_key] if matching_key else 0.0
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
