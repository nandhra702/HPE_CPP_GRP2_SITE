import requests
import webbrowser
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

@csrf_exempt
def dolos_check_view(request):
    if request.method == 'POST':
        try:
            zip_file_path = '/home/sukhraj/dolos/test_submissions.zip'  # Your existing ZIP

            with open(zip_file_path, 'rb') as f:
                res = requests.post(
                    'http://localhost:8080/api/analyze',
                    files={'file': ('dolos_input.zip', f, 'application/zip')}
                )

            if res.status_code == 200:
                report_url = res.json().get('url')
                full_url = f"http://localhost:8000{report_url}"
                webbrowser.open(full_url)
                return HttpResponse(f"<h3>✅ Report opened: <a href='{full_url}' target='_blank'>{full_url}</a></h3>")
            else:
                return HttpResponse(f"❌ Error {res.status_code}: {res.text}")
        except Exception as e:
            return HttpResponse(f"❌ Exception occurred: {str(e)}")

    return render(request, 'judge/dolos_button.html')
