########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\manage.py total lines 46 
########################################################################

"""
(Roadmap 1.C, 3.1)
Main entry point for Gunicorn and Flask CLI.
Modernized for Flask 3.x compliance.
"""
import os
import sys
import click
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
try:
    import config as config_module
except ImportError:
    print("[BOOT][FATAL] 'config.py' not found in root. Path insertion failed.", file=sys.stderr)
    sys.exit(1)
from app import create_app, db, sockets
from app.db.pragma import apply_pragma_on_connect # (Roadmap 1.C)
CONFIG_MAP = {
    'development': config_module.DevelopmentConfig,
    'production': config_module.ProductionConfig,
    'testing': config_module.TestingConfig,
    'default': config_module.Config
}
config_name = os.getenv('FLASK_CONFIG', 'default')
config_class = CONFIG_MAP.get(config_name)
if not config_class:
    print(f"[BOOT][WARN] Unknown FLASK_CONFIG='{config_name}'. Falling back to default Config.")
    config_class = config_module.Config
app = create_app(config_class)
@app.cli.command("apply-pragma")
def apply_pragma_command():
    """Applies optimal PRAGMA settings to the DB."""
    print("Applying PRAGMA settings...")
    with app.app_context():
        apply_pragma_on_connect(db.engine)
    print("PRAGMA settings applied.")
if __name__ == '__main__':
    print(f"[Manage] Starting app with config: {config_name}...")
    sockets.run(app, host=app.config.get('FLASK_HOST', '0.0.0.0'),
                port=int(app.config.get('FLASK_PORT', 8000)),
                allow_unsafe_werkzeug=True)
