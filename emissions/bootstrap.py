import os
import threading

from django.core.management import call_command
from django.db import connection

_boot_lock = threading.Lock()
_boot_done = False


def ensure_demo_database():
    """Prepare the ephemeral demo database used by serverless deployments."""
    global _boot_done
    if _boot_done:
        return
    if os.environ.get('AUTO_BOOTSTRAP_DB', '1') != '1':
        return
    with _boot_lock:
        if _boot_done:
            return
        tables = connection.introspection.table_names()
        if 'emissions_tenant' not in tables:
            call_command('migrate', interactive=False, verbosity=0)
        call_command('seed_demo', verbosity=0)
        _boot_done = True
