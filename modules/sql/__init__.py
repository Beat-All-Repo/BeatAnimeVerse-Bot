"""
SQL layer for BeatVerse modules.
Uses NeonDB (PostgreSQL via SQLAlchemy) when DATABASE_URL is set.
Falls back to NoOp stub when only MongoDB is configured.
"""
import time as _time
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

_DB_URI = os.getenv("DATABASE_URL", "")
_MONGO_URI = os.getenv("MONGO_DB_URI", "")

import logging as _log
log = _log.getLogger(__name__)

BASE = declarative_base()

if _DB_URI:
    _uri = _DB_URI
    if _uri.startswith("postgres://"):
        _uri = _uri.replace("postgres://", "postgresql://", 1)

    def start() -> scoped_session:
        engine = create_engine(
            _uri,
            client_encoding="utf8",
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 10},
        )
        log.info("[SQL] Connecting to NeonDB/PostgreSQL...")
        BASE.metadata.bind = engine
        BASE.metadata.create_all(engine)
        return scoped_session(sessionmaker(bind=engine, autoflush=False))

    for _attempt in range(5):
        try:
            SESSION = start()
            log.info("[SQL] ✅ PostgreSQL connected")
            break
        except Exception as e:
            if _attempt < 4:
                log.warning(f"[SQL] attempt {_attempt+1}/5 failed: {e}. Retrying in 3s...")
                _time.sleep(3)
            else:
                log.error("[SQL] All connection attempts failed. SQL modules will use stub.")
                SESSION = None
                break

elif _MONGO_URI:
    log.info("[SQL] No DATABASE_URL — SQL modules running in stub mode (MongoDB active)")
    SESSION = None
else:
    log.error("[SQL] No database configured!")
    SESSION = None

# NoOp stub if no SQL connection
if SESSION is None:
    class _NoOpSession:
        def query(self, *a, **kw):    raise RuntimeError("No PostgreSQL DB configured")
        def add(self, *a, **kw):      pass
        def delete(self, *a, **kw):   pass
        def commit(self, *a, **kw):   pass
        def close(self, *a, **kw):    pass
        def execute(self, *a, **kw):  pass
    SESSION = _NoOpSession()
