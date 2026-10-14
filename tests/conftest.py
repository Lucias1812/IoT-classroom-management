import sys
import os

# Add master_pi to path so relative imports in socket_server.py resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'master_pi'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
