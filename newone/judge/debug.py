
# Contest-related debug settings
CONTEST_REJOIN_DEBUG = True  # Allow users to rejoin contests after exiting (useful for testing)
CONTEST_TEMPLATE_DEBUG = True  # Enable debug features in contest templates

# Proctoring debug settings
PROCTORING_DEBUG = True  # Enable proctoring debug features

# General contest debug settings
GENERAL_CONTEST_DEBUG = True  # General contest debugging features

# You can easily disable all debug features by setting this to False
MASTER_DEBUG_ENABLED = True

def get_contest_rejoin_debug():
    """Get the contest rejoin debug setting"""
    return MASTER_DEBUG_ENABLED and CONTEST_REJOIN_DEBUG

def get_contest_template_debug():
    """Get the contest template debug setting"""
    return MASTER_DEBUG_ENABLED and CONTEST_TEMPLATE_DEBUG

def get_proctoring_debug():
    """Get the proctoring debug setting"""
    return MASTER_DEBUG_ENABLED and PROCTORING_DEBUG

def get_general_contest_debug():
    """Get the general contest debug setting"""
    return MASTER_DEBUG_ENABLED and GENERAL_CONTEST_DEBUG