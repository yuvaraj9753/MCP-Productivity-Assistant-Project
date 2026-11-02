import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("DATABASE_URL not found in .env")

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
)

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT version()")
        )
        print("Connected to PostgreSQL successfully!")
        print(result.scalar())

except Exception as error:
    print("Database connection failed.")
    print(f"Error: {error}")

finally:
    engine.dispose()