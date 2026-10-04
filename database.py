import os

from dotenv import load_dotenv
from supabase import create_client, Client
from werkzeug.security import generate_password_hash


# Load .env for local development
load_dotenv()


SUPABASE_URL = os.environ.get("SUPABASE_URL")

SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY"
)


if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL is missing."
    )

if not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_SERVICE_ROLE_KEY is missing."
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def get_db():
    return supabase


def hash_password(password):
    return generate_password_hash(password)


def init_database():

    db = get_db()

    print("Checking Supabase connection...")

    try:

        db.table("users") \
            .select("id") \
            .limit(1) \
            .execute()

        print(
            "Supabase connection successful!"
        )

    except Exception as e:

        print(
            "Supabase connection failed:"
        )

        print(e)

        return

    # ADMIN
    try:

        response = (
            db.table("users")
            .select("id")
            .eq("username", "admin")
            .limit(1)
            .execute()
        )

        if not response.data:

            db.table("users").insert({

                "username": "admin",

                "password": hash_password(
                    "admin123"
                ),

                "full_name":
                    "System Administrator",

                "role": "admin"

            }).execute()

            print("Default admin created.")

        else:

            print("Admin already exists.")

    except Exception as e:

        print("Admin creation error:")
        print(e)

    # STUDENT
    try:

        response = (
            db.table("users")
            .select("id")
            .eq("username", "student1")
            .limit(1)
            .execute()
        )

        if not response.data:

            db.table("users").insert({

                "username": "student1",

                "password": hash_password(
                    "student123"
                ),

                "email":
                    "student1@test.com",

                "full_name":
                    "Test Student",

                "role": "student"

            }).execute()

            print("Default student created.")

        else:

            print("Student already exists.")

    except Exception as e:

        print("Student creation error:")
        print(e)

    print(
        "Database initialization completed."
    )


if __name__ == "__main__":
    init_database()