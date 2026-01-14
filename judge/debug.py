"""
Debug Configuration for DMOJ Contest Platform
==============================================

This module contains debug settings and feature toggles for the contest system.
Set MASTER_DEBUG_ENABLED = False to disable all debug features for production.
"""

# =============================================================================
# MASTER SWITCH - Set to False to disable all debug features for production
# =============================================================================
MASTER_DEBUG_ENABLED = True

# =============================================================================
# DEBUG SETTINGS (controlled by MASTER_DEBUG_ENABLED)
# =============================================================================

# Contest-related debug settings
CONTEST_REJOIN_DEBUG = True    # Allow users to rejoin contests after exiting (useful for testing)
CONTEST_TEMPLATE_DEBUG = True    # Enable debug features in contest templates
GENERAL_CONTEST_DEBUG = True     # General contest debugging features

# HPE Contest Backend Connection
# True = enable backend connection, False = frontend-only mode
HPE_BACKEND_CONNECT = True

# Code editor security settings
ALLOW_COPY_PASTE = False          # Allow copy/paste from external sources (for testing)


# =============================================================================
# GETTER FUNCTIONS
# =============================================================================

def get_contest_rejoin_debug():
    """Allow users to rejoin contests after exiting."""
    return MASTER_DEBUG_ENABLED and CONTEST_REJOIN_DEBUG

def get_contest_template_debug():
    """Enable debug features in contest templates."""
    return MASTER_DEBUG_ENABLED and CONTEST_TEMPLATE_DEBUG

def get_general_contest_debug():
    """Enable general contest debugging features."""
    return MASTER_DEBUG_ENABLED and GENERAL_CONTEST_DEBUG

def get_allow_copy_paste():
    """Allow copy/paste from external sources. 
    Returns True to allow external copy/paste, False to block it."""
    return MASTER_DEBUG_ENABLED and ALLOW_COPY_PASTE

def get_hpe_backend_connect():
    """Get the HPE backend connection setting.
    Returns True if backend connection is enabled, False for frontend-only mode.
    Controlled by MASTER_DEBUG_ENABLED.
    """
    return MASTER_DEBUG_ENABLED and HPE_BACKEND_CONNECT