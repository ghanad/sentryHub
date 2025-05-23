# This file makes the 'tests' directory a Python package.

# Import test modules to make them discoverable by Django's test runner
from . import test_context_processors
from . import test_middleware
from . import test_views