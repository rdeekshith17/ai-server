"""
Routes package for SecureGuard Multi-Tenant Platform
"""
from .auth import auth_router, create_auth_routes, get_current_user, require_auth, require_admin, UserRole, UserPermissions, check_permission
from .admin import admin_router, create_admin_routes
from .alerts import alerts_router, create_alerts_routes, send_incident_alert

__all__ = [
    "auth_router",
    "create_auth_routes",
    "get_current_user",
    "require_auth", 
    "require_admin",
    "UserRole",
    "UserPermissions",
    "check_permission",
    "admin_router",
    "create_admin_routes",
    "alerts_router",
    "create_alerts_routes",
    "send_incident_alert"
]
