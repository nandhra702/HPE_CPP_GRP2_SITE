from django.urls import get_resolver
import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dmoj.settings")  # adjust if needed
django.setup()

def recurse(patterns, prefix=""):
    for p in patterns:
        if hasattr(p, 'url_patterns'):
            recurse(p.url_patterns, prefix + str(p.pattern))
        else:
            print(prefix + str(p.pattern), '→', p.callback)

recurse(get_resolver().url_patterns)
