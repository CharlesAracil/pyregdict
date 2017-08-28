import os
import sys

test_folder = os.path.dirname(__file__)
base_folder = os.path.dirname(test_folder)

# if pyregdict is not installed, add its path for current execution
try:
    import pyregdict  # noqa, just testing module import
except ModuleNotFoundError:
    sys.path.append(base_folder)
