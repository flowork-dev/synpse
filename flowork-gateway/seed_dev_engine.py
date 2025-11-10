########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\seed_dev_engine.py total lines 54 
########################################################################

import sys
import os
from werkzeug.security import generate_password_hash
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import create_app
from app.extensions import db
from app.models import User, RegisteredEngine
def get_env_variable(var_name):
    value = os.environ.get(var_name)
    if not value:
        print(f"--- FATAL ERROR: Environment variable {var_name} is not set.")
        sys.exit(1)
    return value
def seed_default_engine():
    print("--- Flowork Gateway Development Engine Seeder ---")
    app = create_app()
    with app.app_context():
        try:
            admin_username = get_env_variable("DEFAULT_ADMIN_USERNAME")
            engine_id = get_env_variable("FLOWORK_ENGINE_ID")
            engine_token = get_env_variable("FLOWORK_ENGINE_TOKEN")
            user = User.query.filter_by(username=admin_username).first()
            if not user:
                print(f"ERROR: Admin user '{admin_username}' not found. Run create_admin.py first.")
                sys.exit(1)
            existing_engine = RegisteredEngine.query.filter_by(id=engine_id).first()
            if existing_engine:
                print(f"Engine ID '{engine_id}' exists. Updating token...")
                existing_engine.engine_token_hash = generate_password_hash(engine_token)
                existing_engine.user_id = user.id
            else:
                print(f"Creating new engine '{engine_id}'...")
                new_engine = RegisteredEngine(
                    id=engine_id,
                    name="Development Engine",
                    user_id=user.id,
                    engine_token_hash=generate_password_hash(engine_token),
                    status='offline'
                )
                db.session.add(new_engine)
            db.session.commit()
            print(f"--- SUCCESS: Default engine '{engine_id}' seeded for user '{admin_username}'. ---")
        except Exception as e:
            db.session.rollback()
            print(f"--- ERROR: Development Engine Seeding Failed: {e} ---")
            raise e
if __name__ == "__main__":
    seed_default_engine()
