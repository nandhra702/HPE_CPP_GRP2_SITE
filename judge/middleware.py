import base64
import hmac
import re
import struct
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import Resolver404, resolve, reverse
from django.utils.encoding import force_bytes
from requests.exceptions import HTTPError

from judge.models import MiscConfig

try:
    import uwsgi
except ImportError:
    uwsgi = None


class ShortCircuitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            callback, args, kwargs = resolve(request.path_info, getattr(request, 'urlconf', None))
        except Resolver404:
            callback, args, kwargs = None, None, None

        if getattr(callback, 'short_circuit_middleware', False):
            return callback(request, *args, **kwargs)
        return self.get_response(request)


class DMOJLoginMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = request.profile = request.user.profile
            if uwsgi:
                uwsgi.set_logvar('username', request.user.username)
                uwsgi.set_logvar('language', request.LANGUAGE_CODE)

            logout_path = reverse('auth_logout')
            login_2fa_path = reverse('login_2fa')
            webauthn_path = reverse('webauthn_assert')
            change_password_path = reverse('password_change')
            change_password_done_path = reverse('password_change_done')
            has_2fa = profile.is_totp_enabled or profile.is_webauthn_enabled
            if (has_2fa and not request.session.get('2fa_passed', False) and
                    request.path not in (login_2fa_path, logout_path, webauthn_path) and
                    not request.path.startswith(settings.STATIC_URL)):
                return HttpResponseRedirect(login_2fa_path + '?next=' + quote(request.get_full_path()))
            elif (request.session.get('password_pwned', False) and
                    request.path not in (change_password_path, change_password_done_path,
                                         login_2fa_path, logout_path) and
                    not request.path.startswith(settings.STATIC_URL)):
                return HttpResponseRedirect(change_password_path + '?next=' + quote(request.get_full_path()))
        else:
            request.profile = None
        return self.get_response(request)


class DMOJImpersonationMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_impersonate:
            if uwsgi:
                uwsgi.set_logvar('username', f'{request.impersonator.username} as {request.user.username}')
            request.no_profile_update = True
            request.profile = request.user.profile
        return self.get_response(request)


class ContestMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        profile = request.profile
        if profile:
            profile.update_contest()
            request.participation = profile.current_contest
            request.in_contest = request.participation is not None
        else:
            request.in_contest = False
            request.participation = None
        return self.get_response(request)


class APIMiddleware(object):
    header_pattern = re.compile('^Bearer ([a-zA-Z0-9_-]{48})$')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        full_token = request.headers.get('authorization', '')
        if not full_token:
            return self.get_response(request)

        token = self.header_pattern.match(full_token)
        if not token:
            return HttpResponse('Invalid authorization header', status=400)
        if request.path.startswith(reverse('admin:index')):
            return HttpResponse('Admin inaccessible', status=403)

        try:
            id, secret = struct.unpack('>I32s', base64.urlsafe_b64decode(token.group(1)))
            request.user = User.objects.get(id=id)

            # User hasn't generated a token
            if not request.user.profile.api_token:
                raise HTTPError()

            # Token comparison
            digest = hmac.new(force_bytes(settings.SECRET_KEY), msg=secret, digestmod='sha256').hexdigest()
            if not hmac.compare_digest(digest, request.user.profile.api_token):
                raise HTTPError()

            request._cached_user = request.user
            request.csrf_processing_done = True
            request.session['2fa_passed'] = True
        except (User.DoesNotExist, HTTPError):
            response = HttpResponse('Invalid token')
            response['WWW-Authenticate'] = 'Bearer realm="API"'
            response.status_code = 401
            return response
        return self.get_response(request)


class MiscConfigDict(dict):
    __slots__ = ('language', 'site', 'backing')

    def __init__(self, language='', domain=None):
        self.language = language
        self.site = domain
        self.backing = None
        super().__init__()

    def __missing__(self, key):
        if self.backing is None:
            cache_key = 'misc_config'
            backing = cache.get(cache_key)
            if backing is None:
                backing = dict(MiscConfig.objects.values_list('key', 'value'))
                cache.set(cache_key, backing, 86400)
            self.backing = backing

        keys = ['%s.%s' % (key, self.language), key] if self.language else [key]
        if self.site is not None:
            keys = ['%s:%s' % (self.site, key) for key in keys] + keys

        for attempt in keys:
            result = self.backing.get(attempt)
            if result is not None:
                break
        else:
            result = ''

        self[key] = result
        return result


class MiscConfigMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        domain = get_current_site(request).domain
        request.misc_config = MiscConfigDict(language=request.LANGUAGE_CODE, domain=domain)
        return self.get_response(request)


class HPEAccessRestrictionMiddleware:
    """
    Restricts non-admin users to only access HPE contest pages.
    Admin/staff users can access the full site.
    Also handles login from the access restricted page.
    """
    
    # Paths that are always allowed for all users
    ALLOWED_PATH_PREFIXES = (
        '/hpe/',           # HPE contest pages
        '/accounts/',      # Login, logout, password reset
        '/login/',         # Social auth login (Google, etc.)
        '/complete/',      # Social auth completion
        '/static/',        # Static files
        '/favicon',        # Favicon
        '/api/',           # API endpoints (have their own auth)
        '/ajax/',          # AJAX endpoints 
        '/problem/',       # Problem pages (needed for contest submissions)
        '/src/',           # Submission source
        '/submission/',    # Submission status
    )
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        path = request.path
        
        # Always allow certain paths
        for prefix in self.ALLOWED_PATH_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)
        
        # Allow static files
        if hasattr(settings, 'STATIC_URL') and path.startswith(settings.STATIC_URL):
            return self.get_response(request)
        
        # If user is not authenticated, show access restricted page with login form
        # (continues to the access restricted logic below)
        
        # Allow admins, staff, and superusers everywhere (only for authenticated users)
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return self.get_response(request)
            
            # Check if user has admin-level permissions
            if request.user.has_perm('judge.edit_all_contest'):
                return self.get_response(request)
        
        # For regular users, show access restricted page or handle login/logout
        from django.shortcuts import render
        from django.contrib.auth import authenticate, login, logout
        
        error = None
        
        # Handle form submissions
        if request.method == 'POST':
            action = request.POST.get('action', '')
            
            if action == 'logout':
                # Logout current user and show login form
                logout(request)
                return HttpResponseRedirect(request.get_full_path())
            
            elif action == 'login':
                username = request.POST.get('username', '').strip()
                password = request.POST.get('password', '')
                
                if username and password:
                    # Authenticate the new user
                    new_user = authenticate(request, username=username, password=password)
                    
                    if new_user is not None:
                        # Login new user
                        login(request, new_user)
                        
                        # Check if new user has access
                        if new_user.is_staff or new_user.is_superuser or new_user.has_perm('judge.edit_all_contest'):
                            # Redirect to the originally requested page
                            return HttpResponseRedirect(request.get_full_path())
                        else:
                            # User logged in but doesn't have admin access
                            # Logout them and show error
                            logout(request)
                            error = 'This account does not have admin access. Please use an admin account.'
                    else:
                        error = 'Invalid username or password.'
                else:
                    error = 'Please enter both username and password.'
        
        return render(request, 'hpe_admin/access_restricted.html', {'error': error}, status=403)


