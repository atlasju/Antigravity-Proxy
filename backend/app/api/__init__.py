"""
API Routes Module

Exposes all route modules for registration in main app.
"""
from . import routes_management
from . import routes_openai
from . import routes_claude
from . import routes_import
from . import routes_gemini
from . import routes_oauth
from . import routes_quota
from . import routes_mapping
from . import routes_images

__all__ = ["routes_management", "routes_openai", "routes_claude", "routes_import", "routes_gemini", "routes_oauth", "routes_quota", "routes_mapping", "routes_images"]
