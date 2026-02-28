"""Runtime Supabase client factory for storage wiring."""

from __future__ import annotations

import os

from supabase import create_client


def create_supabase_client():
    """Build a supabase-py client from runtime environment."""
    url = os.getenv("SUPABASE_PUBLIC_URL")
    key = os.getenv("LEON_SUPABASE_SERVICE_ROLE_KEY")
    if not url:
        raise RuntimeError("SUPABASE_PUBLIC_URL is required for Supabase storage runtime.")
    if not key:
        raise RuntimeError("LEON_SUPABASE_SERVICE_ROLE_KEY is required for Supabase storage runtime.")
    # @@@runtime-factory-fail-loud - storage runtime must fail fast when DSN/key is missing instead of silently falling back.
    return create_client(url, key)
