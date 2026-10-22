import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings
from backend.database.base import Base

logger = logging.getLogger("uvicorn.error")

def init_engine():
    candidate_urls = [
        settings.DATABASE_URL,
        "mysql+mysqlconnector://root:password@localhost:3307/uet_algorithm_battle",
        "mysql+mysqlconnector://root:password@localhost:3306/uet_algorithm_battle",
    ]
    for url in candidate_urls:
        if not url:
            continue
        try:
            mysql_engine = create_engine(url, pool_pre_ping=True)
            with mysql_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[DATABASE] Ket noi MySQL thanh cong tai: {url.split('@')[-1]}!")
            return mysql_engine
        except Exception:
            pass

    print("[DATABASE INFO] Chua bat MySQL. Tu dong chuyen sang SQLite (uet_algorithm_battle.db) de dam bao he thong hoat dong ngay lap tuc!")
    sqlite_engine = create_engine(
        settings.SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False}
    )
    return sqlite_engine

engine = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def auto_migrate():
    try:
        import backend.models
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[DATABASE MIGRATION WARNING]: {e}")

auto_migrate()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()