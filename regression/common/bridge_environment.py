"""Load the external read-only Bridge using the configured project path."""
import os
from pathlib import Path
from dotenv import dotenv_values
from virtuoso_bridge.env import load_vb_env
from .project import ROOT

def load_bridge_environment():
    configured=os.environ.get('VIRTUOSO_BRIDGE_ROOT') or dotenv_values(ROOT/'.env')['VIRTUOSO_BRIDGE_ROOT']
    if not configured:raise ValueError('Configure VIRTUOSO_BRIDGE_ROOT in the project .env')
    load_vb_env(explicit=str(Path(configured)/'.env'))
