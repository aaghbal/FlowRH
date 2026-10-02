import sys
import os

# Ensure the project directory is in the Python path
project_path = os.path.dirname(__file__)
sys.path.insert(0, project_path)

# numpy's bundled OpenBLAS sizes its thread pool from the machine's core count,
# which on a shared host means 64 threads against a per-account process limit.
# Every thread it fails to create costs a retry and an error line, delaying
# startup by tens of seconds. This project only uses numpy through pandas, for
# reading and writing spreadsheets, so a single thread loses nothing.
# setdefault, so a deployment that wants more can still set these.
for _var in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_var, "1")

# Import the WSGI application from horilla.wsgi
from horilla.wsgi import application

# Expose this as "application" for Passenger
application = application
