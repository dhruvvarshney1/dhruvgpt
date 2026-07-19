"""Manual smoke-test for the NVIDIA streaming client.

Run from the ``backend/`` directory with the venv activated::

    python scripts/test_nvidia_client.py

Requires a valid ``.env`` with ``NVIDIA_API_KEY`` set.
"""

import asyncio
import sys
import os

# Ensure the backend package is importable when running as a script.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main() -> None:
    # Import after sys.path fix so app.config can find .env
    from app.nvidia_client import stream_chat_completion, get_full_completion

    test_messages = [
        {"role": "user", "content": "What is the capital of France? Reply in one sentence."},
    ]

    # ── Streaming test ─────────────────────────────────────────────────
    print("=== Streaming test ===")
    usage: dict = {}
    async for chunk in stream_chat_completion(test_messages, usage_out=usage):
        print(chunk, end="", flush=True)
    print("\n")

    if usage:
        print(f"Token usage: {usage}")
    else:
        print("(no usage data returned)")

    # ── Non-streaming test ─────────────────────────────────────────────
    print("\n=== Full completion test ===")
    usage2: dict = {}
    result = await get_full_completion(test_messages, usage_out=usage2)
    print(result)
    if usage2:
        print(f"Token usage: {usage2}")


if __name__ == "__main__":
    asyncio.run(main())
