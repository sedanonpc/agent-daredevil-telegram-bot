#!/usr/bin/env python3
"""
Test OpenAI API Key
===================
Loads .env, validates presence of OPENAI_API_KEY, lists models via OpenAI SDK,
and performs a lightweight embeddings request to verify the key works.
"""

import os
import sys
import traceback

from dotenv import load_dotenv

def mask(value: str, show: int = 8) -> str:
    if not value:
        return ""
    return (value[:show] + "…") if len(value) > show else value

def main() -> int:
    print("🚀 OpenAI API Key Diagnostic")
    print("=" * 40)

    # Ensure UTF-8 in Windows console
    if sys.platform.startswith('win'):
        try:
            os.system('chcp 65001 >nul 2>&1')
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Load environment
    load_dotenv()

    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        print("❌ OPENAI_API_KEY is not set. Create a .env file or export the variable.")
        return 1

    print(f"✅ OPENAI_API_KEY detected: {mask(key)}")

    # Lazy import after loading env
    try:
        import openai
        client = openai.OpenAI(api_key=key)
    except Exception as e:
        print("❌ Failed to initialize OpenAI client:", str(e))
        return 1

    # Step 1: List models (simple permission/billing check)
    try:
        print("\n🔎 Listing available models…")
        models = client.models.list()
        model_ids = [m.id for m in getattr(models, 'data', [])]
        print(f"   ✅ Retrieved {len(model_ids)} models")
        if model_ids:
            print("   e.g.:", ", ".join(model_ids[:5]))
    except Exception as e:
        print("   ❌ Unable to list models.")
        print("      →", str(e))
        # Continue to embeddings test; some orgs restrict model listing

    # Step 2: Very small embeddings call (cheap, verifies key usability)
    try:
        print("\n🧪 Creating a tiny embedding with text-embedding-3-small…")
        _ = client.embeddings.create(
            model="text-embedding-3-small",
            input="hello world"
        )
        print("   ✅ Embeddings request succeeded")
    except Exception as e:
        print("   ❌ Embeddings request failed:")
        print("      →", str(e))
        # Provide hints based on common errors
        msg = str(e).lower()
        if "401" in msg or "unauthorized" in msg or "invalid" in msg:
            print("      Hint: The API key may be invalid or tied to the wrong organization.")
        if "429" in msg or "rate" in msg or "quota" in msg or "billing" in msg:
            print("      Hint: You may be rate-limited or lack billing access/credits.")
        return 2

    print("\n🎉 OpenAI API key appears to be valid and working!")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n👋 Cancelled by user")
        raise SystemExit(130)
    except Exception:
        print("\n❌ Unexpected error:")
        print(traceback.format_exc())
        raise SystemExit(1)


