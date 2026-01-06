from django.urls import path
from .admin import hpe_admin_site

urlpatterns = [
    path('', hpe_admin_site.urls),
]
