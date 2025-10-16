import os
import time
import socket
from urllib.parse import urlparse
from sqlmodel import create_engine, SQLModel
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# Configure engine with safer defaults for cloud providers (Supabase/Render)
connect_args = {}
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

if DATABASE_URL.lower().startswith("postgresql"):
    # Ensure SSL is required and use small pools for web dynos
    connect_args["sslmode"] = os.getenv("DB_SSLMODE", "require")
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "5")),
    })
    # Prefer IPv4 hostaddr to avoid IPv6 egress issues on some platforms
    force_ipv4 = os.getenv("DB_FORCE_IPV4", "true").lower() == "true"
    try:
        parsed = urlparse(DATABASE_URL)
        hostname = parsed.hostname
        if force_ipv4 and hostname:
            infos = socket.getaddrinfo(hostname, None, family=socket.AF_INET)
            if infos:
                ipv4_addr = infos[0][4][0]
                # hostaddr informs libpq to connect using IPv4, keep original host for auth/reference
                connect_args["hostaddr"] = ipv4_addr
                connect_args["host"] = hostname
    except Exception:
        # Non-fatal; continue without hostaddr
        pass

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)

def create_db_and_tables(retries: int = 5, delay: float = 2.0):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            SQLModel.metadata.create_all(engine)
            return
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(delay)
            else:
                raise last_err
