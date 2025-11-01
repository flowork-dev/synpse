#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\extensions.py JUMLAH BARIS 19 
#######################################################################

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
from flask_compress import Compress
db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()
compress = Compress()
metrics = PrometheusMetrics(app=None) # metrics tetap berguna
cors = CORS()
