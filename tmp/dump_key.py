import os
from database.auth_db import get_api_key_for_tradingview

def main():
    try:
        key = get_api_key_for_tradingview('avinash')
        if key:
            preview = f"API key length: {len(key)}\nAPI key preview: {key[:4]}...{key[-4:]}\n"
            print(preview)
            with open('tmp/dump_key_out.txt', 'w', encoding='utf-8') as f:
                f.write(preview)
        else:
            msg = "No API key found for user avinash\n"
            print(msg)
            with open('tmp/dump_key_out.txt', 'w', encoding='utf-8') as f:
                f.write(msg)
    except Exception as e:
        import traceback
        err = f"Error: {e}\n{traceback.format_exc()}\n"
        print(err)
        with open('tmp/dump_key_out.txt', 'w', encoding='utf-8') as f:
            f.write(err)

if __name__ == "__main__":
    main()

