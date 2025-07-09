from django.http import FileResponse
import time
import tempfile
import shutil
import os
import zipfile
import subprocess
import socket
from judge.models import ContestSubmission, SubmissionSource

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

def find_free_port(start_port=3001, max_port=3100, used_ports=set()):
    for port in range(start_port, max_port): #very important to find free ports that are there. 
        if port in used_ports:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(('localhost', port)) != 0:
                used_ports.add(port)  # mark as used 
                return port
    raise RuntimeError("No free port found in range.")


def download_problem_submissions(request, contest_key, problem_code):
    tmp_dir = tempfile.mkdtemp()
    lang_zip_paths = []

    try:
        # Firstly we fetch all submissions for the given problem and given contest
        submissions = ContestSubmission.objects.select_related(
            'submission', 'submission__language', 'submission__user',
            'problem__problem', 'problem__contest'
        ).filter(
            problem__problem__code=problem_code,
            problem__contest__key=contest_key,
            submission__result='AC' 
        )

        #  Group submissions by language
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

            if lang not in lang_buckets:
                lang_buckets[lang] = []
            lang_buckets[lang].append((filename, code))
            print(f"[DBG] Added {filename} under language bucket: {lang}")


        # Create ZIPs (seperate_language_wise) and run Dolos command for web view
        used_ports = set()  #tracks what all ports have been occupied, which ones are empty

        for lang, files in lang_buckets.items():
            zip_filename = f"{lang.replace(' ', '_')}_submissions.zip"
            zip_path = os.path.join(tmp_dir, zip_filename)
            lang_zip_paths.append(zip_path)

            # Write ZIP
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename, code in files:
                    zipf.writestr(filename, code)
                    print(f"[ZIP] Writing {filename} to {zip_filename}")

            # Run Dolos
            lang_flag = DOLOS_LANGUAGE_FLAGS.get(lang, None)
            if lang_flag:
                try:
                    free_port = find_free_port(start_port=3001,used_ports=used_ports)
                    print(f"Running Dolos on port {free_port} for {lang}")
                    subprocess.Popen([
                        #creating the dolos command to be run. we can add flags here to run the command 
                        "dolos", "run", "-f", "web", "-l", lang_flag,
                        "--port", str(free_port), zip_path
                       
                    ])
                except subprocess.CalledProcessError as e:
                    print(f"[✗] Dolos failed for {zip_filename}: {e}")
                except RuntimeError as e:
                    print(f"[!] Could not find free port: {e}")
            else:
                print(f"[!] Skipping Dolos: No language flag for '{lang}'")

        #  Final ZIP with all language ZIPs
        final_zip_path = os.path.join(tmp_dir, f"{problem_code}_grouped_submissions.zip")
        with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as final_zip:
            for zip_file in lang_zip_paths:
                arcname = os.path.basename(zip_file)
                final_zip.write(zip_file, arcname=arcname)

        return FileResponse(open(final_zip_path, 'rb'), as_attachment=True,
                            filename=f"{problem_code}_grouped_submissions.zip")

    finally:
        print("thanks")
        #we will add cleaning up later
        #print("[!] Delaying temp directory cleanup to allow Dolos processes to read files...")
        #time.sleep(45)  # wait for 45 seconds before cleanup : >>TO CHECK IF NEEDED 
        #shutil.rmtree(tmp_dir)

