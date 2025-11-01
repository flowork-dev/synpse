#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\manage.py JUMLAH BARIS 16 
#######################################################################

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import create_app, db
from flask_migrate import Migrate
app = create_app()
Migrate(app, db)
if __name__ == "__main__":
    print("Migration management script ready.")
