from django.http import FileResponse
from django.contrib.auth.models import User
import tempfile
import os
import zipfile
import subprocess
import csv
from collections import defaultdict
import socket
from judge.models import Contest, ContestSubmission, SubmissionSource, SimilarityScore
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


#form the CSV file, reads the similarity score
def extract_similarity_data(report_csv_paths,contest_key):
    similarity_data = defaultdict(lambda: defaultdict(float))  # username -> problem_code -> max_similarity

    for path in report_csv_paths:
        if not os.path.exists(path):
            print(f"[!] Missing Dolos output: {path}")

        # Extract problem code from directory name instead of filename
        parent_dir = os.path.basename(os.path.dirname(path))  # e.g. dolos-report-*-twosumPython3submissions
        problem_code = parent_dir.split('-')[-1]  # Extracts 'twosumPython3submissions'
        
        # Optional cleanup: remove 'submissions' suffix
        if problem_code.endswith('submissions'):
            problem_code = problem_code[:-11]  # now just 'twosumPython3' so removed the word 


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

    
    #storing in a database
    for username, problems in similarity_data.items():
        for problem_code, score in problems.items():
            contest = Contest.objects.get(key=contest_key)
            user = User.objects.get(username=username)

            SimilarityScore.objects.update_or_create(
                contest=contest,
                user=user,
                problem_code=problem_code,
                defaults={'similarity_percent': score * 100}
)




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

    #THIS PREVENTS ANYONE FROM DIRECTLY TYPING IN URL TO download_problem_submission on the net
    if not request.user.is_authenticated or not contest.authors.filter(id=request.user.id).exists():
        return HttpResponseForbidden("You are not allowed to access this resource.")

    problems = contest.problems.all()
    base_dir = "/home/trishal/submissions"  # or any path you want
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

        sim_data = extract_similarity_data(report_csv_paths, contest_key)       
        for username, scores in sim_data.items():
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                print(f"[!] User '{username}' not found in database.")
                continue

            for problem in problems:
                code = problem.code
                matching_key = next((k for k in scores if code in k), None)
                sim_percent = (scores[matching_key] * 100) if matching_key else 0.0

                SimilarityScore.objects.update_or_create(
                    contest=contest,
                    user=user,
                    problem_code=code,
                    defaults={'similarity_percent': sim_percent}
        )
        
        final_zip_path = os.path.join(tmp_dir, f"{contest_key}_grouped_submissions.zip")
        with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as final_zip:
            for zip_file in lang_zip_paths:
                arcname = os.path.basename(zip_file)  
                final_zip.write(zip_file, arcname=arcname)


        return FileResponse(open(final_zip_path, 'rb'), as_attachment=True,
                            filename=f"{contest_key}_grouped_submissions.zip")

    finally:
        print("[✓] Finished preparing submissions and running Dolos.")
#<<<<<<< HEAD


#CREATING THE TABLE TO BE DISPLAYED


def read_similarity_matrix(contest_key):
    try:
        contest = Contest.objects.get(key=contest_key)
    except Contest.DoesNotExist:
        return [], []

    scores = SimilarityScore.objects.filter(contest=contest)
    if not scores.exists():
        return [], []

    users = sorted(set(s.user.username for s in scores))

    # Strip language suffixes from problem_code
    def normalize_problem_code(code):
        for lang in ['C', 'C++', 'C++11', 'Python 2', 'Python 3', 'Java', 'Rust', 'Go',
                     'Kotlin', 'Pascal', 'Ruby', 'Haskell', 'Perl', 'Scala', 'JavaScript']:
            suffix = lang.replace(' ', '')  # e.g., 'Python3'
            if code.endswith(suffix):
                return code[:-len(suffix)]
        return code

    normalized_scores = defaultdict(dict)  # normalized_problem -> user -> score

    for score in scores:
        user = score.user.username
        problem = normalize_problem_code(score.problem_code)
        if user not in normalized_scores[problem]:
            normalized_scores[problem][user] = score.similarity_percent
        else:
            # Take the max score if multiple entries for same problem (e.g., Python3 and C++)
            normalized_scores[problem][user] = max(
                normalized_scores[problem][user], score.similarity_percent
            )

    problems = sorted(normalized_scores.keys())
    headers = problems
    rows = []

    for user in users:
        row = [user]
        for problem in problems:
            score = normalized_scores[problem].get(user, 0.0)
            row.append(f"{score:.2f}%")
        rows.append(row)

    return headers, rows


#NOW SHOW THE TABLE

def show_similarity_table(request, contest_key):
    contest = Contest.objects.get(key=contest_key)
    #prevents any random user from accessing it by directly typing in the URL
    if not request.user.is_authenticated or not contest.authors.filter(id=request.user.id).exists():
        return HttpResponseForbidden("You are not allowed to access this resource.")

    headers, rows = read_similarity_matrix(contest_key)
    return render(request, 'contest/show_similarity_table.html', {
        'headers': headers,
        'rows': rows,
    })
