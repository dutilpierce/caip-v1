"""
Lightweight environment and dependency check for CAIP.
"""

import os
import sys

def safe_import_version(module_name: str):
    try:
        module = __import__(module_name)
        return getattr(module, "__version__", "unknown")
    except Exception:
        return None

def main() -> int:
    print("CAIP Doctor")
    print("-----------")

    httpx_version = safe_import_version("httpx")
    supabase_version = safe_import_version("supabase")
    gotrue_version = safe_import_version("gotrue")

    print(f"httpx: {httpx_version or 'not installed'}")
    print(f"supabase: {supabase_version or 'not installed'}")
    print(f"gotrue: {gotrue_version or 'not installed'}")

    missing_env = []
    for key in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if not os.getenv(key):
            missing_env.append(key)

    if missing_env:
        print("\nMissing env vars:")
        for key in missing_env:
            print(f"- {key}")
        print("\nNext action: set missing secrets in Replit, then restart the repl.")
        return 1

    print("\nEnv vars present.")
    print("Next action: run `python db/seed.py`.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
