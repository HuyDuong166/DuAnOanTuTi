import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings
from backend.database.base import Base

logger = logging.getLogger("uvicorn.error")

def fix_db_url(url: str) -> str:
    """Tự động ép kiểu sang driver postgresql+psycopg2 để dùng psycopg2-binary"""
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url

def init_engine():
    # Lấy DATABASE_URL và tự động chuẩn hóa định dạng
    primary_url = fix_db_url(settings.DATABASE_URL)

    candidate_urls = [
        primary_url,
        "mysql+mysqlconnector://root:password@localhost:3307/uet_algorithm_battle",
        "mysql+mysqlconnector://root:password@localhost:3306/uet_algorithm_battle",
    ]
    for url in candidate_urls:
        if not url:
            continue
        try:
            db_engine = create_engine(url, pool_pre_ping=True)
            with db_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            host_info = url.split('@')[-1] if '@' in url else url
            print(f"[DATABASE SUCCESS] Ket noi Database thanh cong tai: {host_info}!")
            return db_engine
        except Exception as e:
            # In trực tiếp lỗi kết nối Neon/Database chính ra Render Log
            if url == primary_url:
                print(f"[DATABASE CONNECTION ERROR ON PRIMARY DB]: {e}")

    print("[DATABASE INFO] Chua bat MySQL/Postgres Cloud. Tu dong chuyen sang SQLite (uet_algorithm_battle.db) de dam bao he thong hoat dong ngay lap tuc!")
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