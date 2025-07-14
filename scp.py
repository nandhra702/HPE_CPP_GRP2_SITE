# print_urls.py
from django.urls import get_resolver
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dmoj.settings")  # adjust if needed
django.setup()

url_patterns = get_resolver().url_patterns

def print_patterns(patterns, prefix=''):
    for pattern in patterns:
        if hasattr(pattern, 'url_patterns'):
            print_patterns(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            print(f"{prefix}{pattern.pattern}  -->  {pattern.callback}")

print_patterns(url_patterns)
