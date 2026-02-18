"""
The ECMWF VORTEX extension package.
"""

# Recursive inclusion of packages with potential FootprintBase classes
from . import data as data
from . import tools as tools

#: No automatic export
__all__ = []

__tocinfoline__ = "The ECMWF VORTEX extension"
