########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\create_admin.py total lines 213 
########################################################################

import sys
import os
import argparse
import secrets
import uuid
from eth_account import Account
from werkzeug.security import generate_password_hash
from getpass import getpass
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import create_app
from app.extensions import db
from app.models import AdminUser, Role, Permission, Plan, User, Subscription, PlanPrice
Account.enable_unaudited_hdwallet_features()
KEY_FILE_PATH = "/app/data/DO_NOT_DELETE_private_key.txt" # English Hardcode
parser = argparse.ArgumentParser(
    description="Flowork Gateway Admin User & Initial Data Seeder"
)
parser.add_argument(
    "--username", default="FLOWORKSYNAPSE", help="Username for the admin and regular user."
)
parser.add_argument(
    "--email",
    default="Anonymous@FLOWORK.CLOUD",
    help="Email for the corresponding regular user.",
)
parser.add_argument(
    "--password", default="b8d91bf93a29f3f504bb7e7b9a2fe90", help="Password for the admin and user."
)
parser.add_argument(
    "--reset", action="store_true", help="Flag to reset password if user exists."
)
parser.add_argument(
    "--show-private-key", # English Hardcode
    action="store_true", # English Hardcode
    help="Force print the generated private key to stdout (for first run)." # English Hardcode
)
args = parser.parse_args()
app = create_app()
with app.app_context():
    print("--- Flowork Gateway Initializer ---") # English Hardcode
    print("--- Ensuring all database tables are created (db.create_all()) ---") # English Hardcode
    try:
        db.create_all()
        print("--- Database tables created/verified successfully. ---") # English Hardcode
    except Exception as e:
        print(f"--- CRITICAL: db.create_all() FAILED: {e} ---") # English Hardcode
        sys.exit(1) # Stop if we can't create tables
    env_username = os.environ.get("DEFAULT_ADMIN_USERNAME")
    env_password = os.environ.get("ADMIN_DEFAULT_PASSWORD")
    username = env_username if env_username else args.username
    email = args.email # (English Hardcode) Email is not in the .env, use arg default
    password = env_password if env_password else args.password
    if env_username:
        print(f"[INFO] Using username from environment: {env_username}")
    if env_password:
        print(f"[INFO] Using password from environment.")
    admin_user_to_modify = AdminUser.query.filter_by(username=username).first()
    if admin_user_to_modify:
        if args.reset:
            print(
                f"Admin User '{username}' exists. Resetting password and verifying roles." # English Hardcode
            )
        else:
            print(f"Skipping admin user creation: '{username}' already exists.") # English Hardcode
    else:
        print(f"Admin User '{username}' not found. Creating new admin user.") # English Hardcode
        admin_user_to_modify = AdminUser(id=str(uuid.uuid4()), username=username)
    admin_user_to_modify.password_hash = generate_password_hash(
        password, method="pbkdf2:sha256"
    )
    superadmin_role = Role.query.filter_by(name="superadmin").first()
    if not superadmin_role:
        print("Creating 'superadmin' role...") # English Hardcode
        superadmin_role = Role(id="superadmin", name="superadmin", description="Full system access") # English Hardcode
        db.session.add(superadmin_role)
    all_permissions = [
        "dashboard:read", "dashboard:read_financial", "plan:read", "plan:update",
        "plan:create", "plan:delete", "users:read", "users:create", "users:update",
        "users:delete", "system:read", "system:update", "features:read",
        "features:create", "features:update", "features:delete",
    ]
    for perm_name in all_permissions:
        permission = Permission.query.filter_by(name=perm_name).first()
        if not permission:
            permission = Permission(id=perm_name, name=perm_name)
            db.session.add(permission)
        if permission not in superadmin_role.permissions:
            superadmin_role.permissions.append(permission)
    if superadmin_role not in admin_user_to_modify.roles:
        admin_user_to_modify.roles.append(superadmin_role)
        print(f"Assigned 'superadmin' role to admin user '{username}'.") # English Hardcode
    if not admin_user_to_modify in db.session:
        db.session.add(admin_user_to_modify)
    print(f"Admin user '{username}' configured.") # English Hardcode
    print("Checking for corresponding regular user...") # English Hardcode
    regular_user = User.query.filter_by(email=email).first()
    if not regular_user:
        print(f"Regular user for '{email}' not found. Creating now...") # English Hardcode
        priv_key_bytes = secrets.token_bytes(32)
        new_account = Account.from_key(priv_key_bytes)
        new_private_key_hex = new_account.key.hex() # Ini string tanpa 0x
        new_public_address = new_account.address # Ini string DENGAN 0x
        if new_private_key_hex.startswith("0x"):
            new_private_key_hex = new_private_key_hex[2:]
        full_private_key = f"0x{new_private_key_hex}"
        try:
            with open(KEY_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(full_private_key) # <-- Writes "0xe533..."
            if args.show_private_key:
                print(f"!!! Private Key securely saved to '{KEY_FILE_PATH}' for retrieval. !!!") # English Hardcode
        except Exception as e:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # English Hardcode
            print(f"!!! CRITICAL: FAILED TO SAVE PRIVATE KEY FILE: {e}               !!!") # English Hardcode
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # English Hardcode
        if args.show_private_key:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # English Hardcode
            print("!!!               CRITICAL: NEW IDENTITY GENERATED                     !!!") # English Hardcode
            print("!!!                                                                    !!!") # English Hardcode
            print(f"!!! Generated NEW Private Key: {full_private_key}") # <-- Prints "0xe533..."
            print(f"!!! Generated Public Address:  {new_public_address}") # English Hardcode
            print("!!!                                                                    !!!") # English Hardcode
            print("!!!   COPY AND SAVE THE 'Generated NEW Private Key' NOW.               !!!") # English Hardcode
            print("!!!   YOU WILL USE THIS TO LOG IN. IT WILL NOT BE SHOWN AGAIN.         !!!") # English Hardcode
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # English Hardcode
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_regular_user = User(
            id=str(uuid.uuid4()), # (English Hardcode) Add 'id' field
            username=username,
            email=email,
            password_hash=hashed_password,
            status="active", # English Hardcode
            public_address=new_public_address
        )
        db.session.add(new_regular_user)
        db.session.flush() # Get the new user ID
        free_subscription = Subscription(id=str(uuid.uuid4()), user_id=new_regular_user.id, tier="architect") # English Hardcode
        db.session.add(free_subscription)
        print(
            f"Successfully created regular user '{username}' with email '{email}' and an architect subscription." # English Hardcode
        )
    else:
        print(
            f"Corresponding regular user with email '{email}' already exists. Skipping creation." # English Hardcode
        )
        if not regular_user.public_address:
            priv_key_bytes = secrets.token_bytes(32)
            new_account = Account.from_key(priv_key_bytes)
            new_private_key_hex = new_account.key.hex() # Ini string tanpa 0x
            new_public_address = new_account.address # Ini string DENGAN 0x
            if new_private_key_hex.startswith("0x"):
                new_private_key_hex = new_private_key_hex[2:]
            full_private_key = f"0x{new_private_key_hex}"
            try:
                with open(KEY_FILE_PATH, "w", encoding="utf-8") as f:
                    f.write(full_private_key) # <-- Writes "0xe533..."
                if args.show_private_key:
                    print(f"!!! Private Key securely saved to '{KEY_FILE_PATH}' for retrieval. !!!") # English Hardcode
            except Exception as e:
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # English Hardcode
                print(f"!!! CRITICAL: FAILED TO SAVE PRIVATE KEY FILE: {e}               !!!") # English Hardcode
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # English Hardcode
            if args.show_private_key:
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # English Hardcode
                print("!!!               CRITICAL: NEW IDENTITY GENERATED (FOR EXISTING USER)   !!!") # English Hardcode
                print(f"!!! Generated NEW Private Key: {full_private_key}") # <-- Prints "0xe533..."
                print(f"!!! Generated Public Address:  {new_public_address}") # English Hardcode
                print("!!!   COPY AND SAVE THE 'Generated NEW Private Key' NOW.               !!!") # English Hardcode
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") # English Hardcode
            regular_user.public_address = new_public_address
            print(f"Updated existing user '{email}' with new public address: {new_public_address}") # English Hardcode
    default_plans_data = {
        "free": {
            "name": "Standard", # English Hardcode
            "description": "Base plan for all users.", # English Hardcode
            "is_public": True,
            "max_executions": None, # Unlimited in Open Core
            "features": [
                "Unlimited Self-Hosted Engines", # English Hardcode
                "Full Workflow Designer Access", # English Hardcode
                "All Core Nodes", # English Hardcode
                "Community Support", # English Hardcode
            ],
            "prices": [], # No pricing tiers for Open Core base plan
        },
    }
    print("\n--- Seeding and Verifying Default Plan Structure ---") # English Hardcode
    for plan_id, data in default_plans_data.items():
        plan = Plan.query.filter_by(id=plan_id).first()
        if not plan:
            print(f"Plan '{plan_id}' not found. Creating it...") # English Hardcode
            plan = Plan(id=plan_id)
            db.session.add(plan)
        plan.name = data["name"]
        plan.description = data["description"]
        plan.is_public = data["is_public"]
        plan.max_executions = data["max_executions"]
        plan.features = data["features"]
        print(f"Plan '{plan_id}' structure configured.") # English Hardcode
        PlanPrice.query.filter_by(plan_id=plan_id).delete()
        print(f"  -> Removed any existing price tiers for '{plan_id}'.") # English Hardcode
    try:
        db.session.commit()
        print("\n--- Initialization Complete ---") # English Hardcode
    except Exception as e:
        db.session.rollback()
        print(f"\n--- Initialization FAILED: {e} ---") # English Hardcode
        print("Please check database connection and schema.") # English Hardcode
