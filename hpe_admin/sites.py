from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class HPEAdminSite(AdminSite):
    site_header = _("HPE Admin")
    site_title = _("HPE Admin Portal")
    index_title = _("HPE Administration")
