
from src.database.connection import get_supabase_client

import os
from dotenv import load_dotenv

load_dotenv()

print("Supabase URL:", os.getenv("SUPABASE_URL"))
print("Secret key loaded:", bool(os.getenv("SUPABASE_SECRET_KEY")))

supabase = get_supabase_client()

response = (
    supabase
    .table("entity_types")
    .select("*")
    .execute()
)

print("Successfully connected to Supabase!")
print(f"Entity types found: {len(response.data)}")

for entity_type in response.data:
    print(entity_type["name"])
