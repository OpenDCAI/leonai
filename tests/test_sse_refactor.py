"""Compatibility entrypoint for PR #51 SSE test command.

PR #51 stated this command explicitly:
`uv run pytest tests/test_sse_refactor.py -x -v`

The maintained SSE regression coverage lives in `tests/test_sse_reconnect.py`.
This shim keeps the stated path runnable post-merge.
"""

from tests.test_sse_reconnect import *  # noqa: F401,F403
