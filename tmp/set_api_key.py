import os
from database.auth_db import upsert_api_key

TARGET_USER = "avinash"
KEY = "dff4df252199a2a9289cb9c5cee2310ecd5a272201697979d88f4cb3b3860cef"

def main():
    try:
        upsert_api_key(TARGET_USER, KEY)
        print(f"API key set for user '{TARGET_USER}'. Length: {len(KEY)}, preview: {KEY[:4]}...{KEY[-4:]}")
    except Exception as e:
        import traceback
        print("Error setting API key:", e)
        traceback.print_exc()

if __name__ == "__main__":
    main()

