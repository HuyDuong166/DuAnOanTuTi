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

# 1. API Xuất toàn bộ mã nguồn Bot (Đã lọc theo tournament_id)
@router.get("/export-bots")
async def export_bots(
    group: str = None, 
    tournament_id: int = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    query = db.query(Bot).filter(Bot.status == "READY")

    # Lọc danh sách Bot đã đăng ký trong Giải đấu
    if tournament_id:
        try:
            from backend.models.tournament import TournamentParticipant
            
            participants = db.query(TournamentParticipant).filter(
                TournamentParticipant.tournament_id == tournament_id
            ).all()

            bot_ids = [p.bot_id for p in participants if getattr(p, "bot_id", None)]
            user_ids = [p.user_id for p in participants if getattr(p, "user_id", None)]

            if bot_ids:
                query = query.filter(Bot.id.in_(bot_ids))
            elif user_ids:
                query = query.filter(Bot.user_id.in_(user_ids))
        except Exception as e:
            print(f"[ADMIN EXPORT WARNING] Bỏ qua lọc TournamentParticipant: {e}")

    bots = query.all()

    if not bots:
        raise HTTPException(
            status_code=400, 
            detail=f"Không tìm thấy Bot READY nào được duyệt trong giải đấu ID {tournament_id}"
        )

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
        raise HTTPException(status_code=400, detail="Tìm thấy Bot nhưng không đọc được nội dung mã nguồn")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=bots_tournament_{tournament_id or 'all'}.zip"}
    )

# Schema nhận dữ liệu kết quả đấu từ Laptop
class MatchResultImport(BaseModel):
    tournament_id: int
    standings: List[Dict[str, Any]]
    match_logs: List[Dict[str, Any]]

# 2. API Nhận Bảng xếp hạng & Match Logs đẩy vào CSDL (Đã sửa lỗi truy cập user)
@router.post("/import-results")
async def import_results(
    data: MatchResultImport,
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    try:
        for item in data.standings:
            bot_id = item.get("bot_id")
            score = item.get("score", 0)
            
            if bot_id:
                bot = db.query(Bot).filter(Bot.id == bot_id).first()
                if bot:
                    # Cập nhật điểm cho Bot
                    if hasattr(bot, "score"):
                        bot.score = (getattr(bot, "score") or 0) + score
                    if hasattr(bot, "elo"):
                        bot.elo = (getattr(bot, "elo") or 1000) + score

                    # Tìm User sở hữu Bot qua `user` hoặc `user_id`
                    owner_user = getattr(bot, "user", None)
                    if not owner_user and hasattr(bot, "user_id") and bot.user_id:
                        owner_user = db.query(User).filter(User.id == bot.user_id).first()

                    # Cập nhật điểm cho User
                    if owner_user and hasattr(owner_user, "score"):
                        owner_user.score = (getattr(owner_user, "score") or 0) + score

        # Cập nhật trạng thái Giải đấu thành COMPLETED
        if hasattr(data, "tournament_id") and data.tournament_id:
            try:
                from backend.models.tournament import Tournament
                tournament = db.query(Tournament).filter(Tournament.id == data.tournament_id).first()
                if tournament:
                    tournament.status = "COMPLETED"
            except Exception as e:
                print(f"[ADMIN] Bỏ qua cập nhật bảng Tournament: {e}")

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