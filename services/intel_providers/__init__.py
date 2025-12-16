"""
Intel Providers Package

Security intelligence data providers for security analysis.
ACLED is the primary source (requires free registration).
MediaStack is a high-quality news fallback (requires API key).
GDELT and RSS are free fallback sources (no API key required).
Fully portable for Windows standalone deployment.
"""

from .gdelt_provider import GDELTProvider
from .rss_provider import RSSProvider
from .official_provider import OfficialProvider
from .acled_provider import ACLEDProvider, is_acled_available
from .mediastack_provider import MediaStackProvider, is_mediastack_available

__all__ = [
    'GDELTProvider', 
    'RSSProvider', 
    'OfficialProvider', 
    'ACLEDProvider', 
    'is_acled_available',
    'MediaStackProvider',
    'is_mediastack_available'
]
