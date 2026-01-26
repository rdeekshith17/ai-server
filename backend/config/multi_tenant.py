# Multi-Tenant Configuration
# SecureGuard Enterprise Platform

# ===========================================
# SUBSCRIPTION PLANS
# ===========================================
PLANS = {
    "trial": {
        "name": "Trial",
        "max_cameras": 2,
        "max_users": 1,
        "max_watchlist": 5,
        "retention_days": 3,
        "features": ["live_detection", "basic_analytics"],
        "price_cents": 0,
        "duration_days": 14
    },
    "basic": {
        "name": "Basic",
        "max_cameras": 4,
        "max_users": 2,
        "max_watchlist": 10,
        "retention_days": 7,
        "features": ["live_detection", "watchlist", "basic_analytics"],
        "price_cents": 9900,  # $99/month
        "gpt_analysis": False
    },
    "professional": {
        "name": "Professional",
        "max_cameras": 16,
        "max_users": 5,
        "max_watchlist": 100,
        "retention_days": 30,
        "features": ["live_detection", "watchlist", "advanced_analytics", "api_access", "gpt_analysis", "webhook_alerts"],
        "price_cents": 29900,  # $299/month
        "gpt_analysis": True
    },
    "enterprise": {
        "name": "Enterprise",
        "max_cameras": 64,
        "max_users": -1,  # Unlimited
        "max_watchlist": -1,  # Unlimited
        "retention_days": 90,
        "features": ["live_detection", "watchlist", "advanced_analytics", "api_access", "gpt_analysis", "webhook_alerts", "custom_branding", "dedicated_support", "sla_99_9"],
        "price_cents": 79900,  # $799/month base
        "gpt_analysis": True
    }
}

# ===========================================
# ROLE PERMISSIONS
# ===========================================
ROLES = {
    "super_admin": {
        "name": "Super Admin",
        "description": "Platform administrator with full access",
        "permissions": ["*"],
        "is_platform_admin": True
    },
    "client_owner": {
        "name": "Owner",
        "description": "Client account owner with full access to their organization",
        "permissions": [
            "view_dashboard",
            "view_live",
            "view_incidents",
            "manage_incidents",
            "manage_cameras",
            "manage_watchlist",
            "view_analytics",
            "manage_users",
            "manage_settings",
            "manage_billing",
            "api_access"
        ]
    },
    "client_manager": {
        "name": "Manager",
        "description": "Can manage cameras, watchlist, and review incidents",
        "permissions": [
            "view_dashboard",
            "view_live",
            "view_incidents",
            "manage_incidents",
            "manage_cameras",
            "manage_watchlist",
            "view_analytics"
        ]
    },
    "client_viewer": {
        "name": "Viewer",
        "description": "View-only access to dashboard and incidents",
        "permissions": [
            "view_dashboard",
            "view_live",
            "view_incidents",
            "view_analytics"
        ]
    },
    "api_only": {
        "name": "API User",
        "description": "Programmatic access via API key only",
        "permissions": [
            "api_access",
            "view_incidents",
            "view_analytics"
        ]
    }
}

# ===========================================
# DETECTION SETTINGS
# ===========================================
DETECTION_SENSITIVITY = {
    "low": {
        "threat_threshold": 0.8,
        "incident_threshold": 0.85,
        "false_positive_tolerance": "high"
    },
    "medium": {
        "threat_threshold": 0.6,
        "incident_threshold": 0.7,
        "false_positive_tolerance": "medium"
    },
    "high": {
        "threat_threshold": 0.4,
        "incident_threshold": 0.5,
        "false_positive_tolerance": "low"
    }
}

# ===========================================
# STREAM PROCESSING SETTINGS
# ===========================================
STREAM_SETTINGS = {
    "default_fps": 2,  # Frames to process per second
    "max_fps": 5,
    "frame_buffer_size": 10,
    "reconnect_attempts": 5,
    "reconnect_delay_seconds": 5,
    "health_check_interval_seconds": 30,
    "frame_ttl_seconds": 5
}

# ===========================================
# ALERT SETTINGS
# ===========================================
ALERT_SETTINGS = {
    "cooldown_seconds": 60,  # Min time between alerts for same camera
    "batch_window_seconds": 5,  # Group alerts within this window
    "max_alerts_per_hour": 100,  # Rate limit per client
    "channels": ["email", "webhook", "sms", "whatsapp"]
}
