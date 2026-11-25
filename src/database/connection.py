
import os

from dotenv import load_dotenv
from supabase import Client, create_client


# Load environment variables from the project root
load_dotenv()


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client.
    """

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url:
        raise ValueError("SUPABASE_URL is missing from .env")

    if not supabase_key:
        raise ValueError("SUPABASE_SECRET_KEY is missing from .env")

    return create_client(supabase_url, supabase_key)
