from hr.models import Employee
from core.models import SiteSettings


def site_settings_processor(request):
    return {'site_settings': SiteSettings.load()}


def user_role_processor(request):
    if not request.user.is_authenticated:
        return {'user_role': None}
    if request.user.is_superuser or request.user.is_staff:
        return {'user_role': 'admin'}
    try:
        return {'user_role': request.user.employee_profile.role}
    except Employee.DoesNotExist:
        return {'user_role': 'staff'}
