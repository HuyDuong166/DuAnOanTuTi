import io
import os
import zipfile
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.user import User
from backend.models.bot import Bot, BotVersion
from backend.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin Workflow"])

def verify_admin(current_user: User = Depends(get_current_user)):
    if not getattr(current_user, "is_admin", False) and getattr(current_user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền truy cập API này")
    return current_user

def get_code_from_object(obj):
    if not obj:
        return None
    for attr in ["source_code", "code", "content", "script", "file_content", "file_path", "code_path"]:
        val = getattr(obj, attr, None)
        if val and isinstance(val, str):
            if os.path.exists(val) and os.path.isfile(val):
                try:
                    with open(val, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
            elif len(val.strip()) > 0:
                return val
    return None

# 1. API Xuất toàn bộ mã nguồn Bot
@router.get("/export-bots")
async def export_bots(
    group: str = None, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    bots = db.query(Bot).filter(Bot.status == "READY").all()

    if not bots:
        raise HTTPException(status_code=400, detail="Không có Bot nào ở trạng thái READY")

    zip_buffer = io.BytesIO()
    exported_count = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for bot in bots:
            code_content = None

            curr_ver = getattr(bot, "current_version", None)
            code_content = get_code_from_object(curr_ver)

            if not code_content:
                code_content = get_code_from_object(bot)

            if not code_content:
                latest_ver = db.query(BotVersion).filter(BotVersion.bot_id == bot.id).order_by(BotVersion.id.desc()).first()
                code_content = get_code_from_object(latest_ver)

            if code_content:
                filename = f"group_{group or 'ALL'}/bot_{bot.id}_user_{bot.user_id}.py"
                zip_file.writestr(filename, code_content)
                exported_count += 1

    if exported_count == 0:
        raise HTTPException(status_code=400, detail="Đã tìm thấy Bot READY nhưng không đọc được nội dung mã nguồn")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=bots_export_{group or 'all'}.zip"}
    )

# Schema nhận dữ liệu kết quả đấu từ Laptop
class MatchResultImport(BaseModel):
    tournament_id: int
    standings: List[Dict[str, Any]]
    match_logs: List[Dict[str, Any]]

# 2. API Nhận Bảng xếp hạng & Match Logs từ Laptop đẩy lên Render
# ✏️ CẬP NHẬT HÀM IMPORT_RESULTS TRONG backend/routers/admin.py
@router.post("/import-results")
async def import_results(
    data: MatchResultImport,
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    try:
        # 1. Cập nhật điểm số và thứ hạng của Bot/User vào CSDL
        for item in data.standings:
            bot_id = item.get("bot_id")
            score = item.get("score", 0)
            
            if bot_id:
                bot = db.query(Bot).filter(Bot.id == bot_id).first()
                if bot:
                    # Cập nhật điểm cho Bot (hoặc thuộc tính điểm tương ứng trong DB của bạn)
                    if hasattr(bot, "score"):
                        bot.score = (getattr(bot, "score") or 0) + score
                    if hasattr(bot, "elo"):
                        bot.elo = (getattr(bot, "elo") or 1000) + score

                    # Cập nhật điểm cho chủ sở hữu Bot (User)
                    if bot.owner and hasattr(bot.owner, "score"):
                        bot.owner.score = (getattr(bot.owner, "score") or 0) + score

        # 2. Cập nhật trạng thái Giải đấu thành Đã Hoàn Thành (COMPLETED)
        if hasattr(data, "tournament_id") and data.tournament_id:
            try:
                from backend.models.tournament import Tournament
                tournament = db.query(Tournament).filter(Tournament.id == data.tournament_id).first()
                if tournament:
                    tournament.status = "COMPLETED"
            except Exception as e:
                print(f"[ADMIN] Không tìm thấy bảng Tournament để cập nhật trạng thái: {e}")

        # 3. Lưu toàn bộ thay đổi vào CSDL
        db.commit()

        print(f"[ADMIN SUCCESS] Đã lưu thành công {len(data.standings)} kết quả vào CSDL Web!")
        return {
            "status": "success", 
            "message": f"Đã cập nhật trực tiếp {len(data.standings)} kết quả lên trang Web!"
        }

    except Exception as e:
        db.rollback()
        print(f"[ADMIN ERROR] Lỗi khi lưu kết quả vào CSDL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu CSDL: {str(e)}")