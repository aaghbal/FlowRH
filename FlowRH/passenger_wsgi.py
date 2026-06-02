import sys
import os

# Ensure the project directory is in the Python path
project_path = os.path.dirname(__file__)
sys.path.insert(0, project_path)

# Import the WSGI application from horilla.wsgi
from horilla.wsgi import application

# Expose this as "application" for Passenger
application = application
