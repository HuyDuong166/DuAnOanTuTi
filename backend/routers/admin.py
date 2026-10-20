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

# 1. API Xuất mã nguồn Bot thuộc Giải đấu
@router.get("/export-bots")
async def export_bots(
    group: str = None, 
    tournament_id: int = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    if not tournament_id:
        raise HTTPException(status_code=400, detail="Thiếu tham số tournament_id!")

    registered_user_ids = []
    registered_bot_ids = []

    try:
        from backend.models.tournament import TournamentParticipant
        participants = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == tournament_id
        ).all()

        for p in participants:
            u_id = getattr(p, "user_id", None)
            b_id = getattr(p, "bot_id", None)
            if u_id: registered_user_ids.append(u_id)
            if b_id: registered_bot_ids.append(b_id)
    except Exception as e:
        print(f"[EXPORTERS] Lỗi đọc TournamentParticipant: {e}")

    bots = []
    if registered_bot_ids:
        bots = db.query(Bot).filter(Bot.id.in_(registered_bot_ids), Bot.status == "READY").all()
    
    if not bots and registered_user_ids:
        bots = db.query(Bot).filter(Bot.user_id.in_(registered_user_ids), Bot.status == "READY").all()

    if not bots:
        raise HTTPException(
            status_code=400, 
            detail=f"Giải đấu ID {tournament_id} chưa có thí sinh nào đăng ký hoặc Bot chưa ở trạng thái READY!"
        )

    zip_buffer = io.BytesIO()
    exported_count = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for bot in bots:
            code_content = get_code_from_object(getattr(bot, "current_version", None)) or get_code_from_object(bot)
            if not code_content:
                latest_ver = db.query(BotVersion).filter(BotVersion.bot_id == bot.id).order_by(BotVersion.id.desc()).first()
                code_content = get_code_from_object(latest_ver)

            if code_content:
                filename = f"group_{group or 'ALL'}/bot_{bot.id}_user_{bot.user_id}.py"
                zip_file.writestr(filename, code_content)
                exported_count += 1

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=bots_tournament_{tournament_id}.zip"}
    )

class MatchResultImport(BaseModel):
    tournament_id: int
    standings: List[Dict[str, Any]]
    match_logs: List[Dict[str, Any]]

# 2. API Cập nhật Bảng xếp hạng, Quán quân và Cây thi đấu
@router.post("/import-results")
async def import_results(
    data: MatchResultImport,
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    try:
        # 1. Cập nhật điểm số
        for item in data.standings:
            bot_id = item.get("bot_id")
            score = item.get("score", 0)
            if bot_id:
                bot = db.query(Bot).filter(Bot.id == bot_id).first()
                if bot:
                    if hasattr(bot, "score"): bot.score = (getattr(bot, "score") or 0) + score
                    if hasattr(bot, "elo"): bot.elo = (getattr(bot, "elo") or 1000) + score

                    owner_user = getattr(bot, "user", None) or (db.query(User).filter(User.id == bot.user_id).first() if hasattr(bot, "user_id") else None)
                    if owner_user and hasattr(owner_user, "score"):
                        owner_user.score = (getattr(owner_user, "score") or 0) + score

        # 2. Cập nhật Nhà Vô Địch theo đúng tên cột thực tế trong CSDL
        if data.tournament_id:
            try:
                from backend.models.tournament import Tournament
                tournament = db.query(Tournament).filter(Tournament.id == data.tournament_id).first()
                if tournament:
                    tour_cols = Tournament.__table__.columns.keys()
                    if "status" in tour_cols:
                        tournament.status = "COMPLETED"

                    if data.standings:
                        winner_bot_id = data.standings[0].get("bot_id")
                        winner_bot = db.query(Bot).filter(Bot.id == winner_bot_id).first()
                        winner_user_id = getattr(winner_bot, "user_id", None) if winner_bot else None

                        if "winner_bot_id" in tour_cols:
                            tournament.winner_bot_id = winner_bot_id
                        if "winner_id" in tour_cols:
                            tournament.winner_id = winner_user_id or winner_bot_id
                        if "winner_user_id" in tour_cols:
                            tournament.winner_user_id = winner_user_id
                        if "winner" in tour_cols:
                            try:
                                setattr(tournament, "winner", winner_user_id or winner_bot_id)
                            except Exception:
                                pass
            except Exception as e:
                print(f"[ADMIN] Lỗi cập nhật Quán quân: {e}")

        # 3. Lưu lịch sử trận đấu bằng cách đọc tên cột CSDL tự động
        if data.match_logs:
            try:
                from backend.models.match import Match
                db.query(Match).filter(Match.tournament_id == data.tournament_id).delete(synchronize_session=False)

                match_cols = Match.__table__.columns.keys()

                for idx, m in enumerate(data.match_logs, start=1):
                    match_kwargs = {}

                    if "tournament_id" in match_cols:
                        match_kwargs["tournament_id"] = data.tournament_id

                    b1 = m.get("bot1_id")
                    if "bot1_id" in match_cols: match_kwargs["bot1_id"] = b1
                    elif "player1_id" in match_cols: match_kwargs["player1_id"] = b1
                    elif "user1_id" in match_cols: match_kwargs["user1_id"] = b1

                    b2 = m.get("bot2_id")
                    if "bot2_id" in match_cols: match_kwargs["bot2_id"] = b2
                    elif "player2_id" in match_cols: match_kwargs["player2_id"] = b2
                    elif "user2_id" in match_cols: match_kwargs["user2_id"] = b2

                    w_id = m.get("winner_id")
                    if "winner_id" in match_cols: match_kwargs["winner_id"] = w_id
                    elif "winner_bot_id" in match_cols: match_kwargs["winner_bot_id"] = w_id

                    if "status" in match_cols: match_kwargs["status"] = "COMPLETED"

                    rnd = m.get("round", 1)
                    if "round" in match_cols: match_kwargs["round"] = rnd
                    elif "round_num" in match_cols: match_kwargs["round_num"] = rnd

                    if "match_number" in match_cols: match_kwargs["match_number"] = idx

                    log_str = str(m.get("log", ""))
                    if "log" in match_cols: match_kwargs["log"] = log_str
                    elif "logs" in match_cols: match_kwargs["logs"] = log_str

                    # Đảm bảo không bị dính lỗi non-nullable column
                    for col in Match.__table__.columns:
                        if not col.nullable and col.default is None and col.name not in match_kwargs and not col.primary_key and not col.autoincrement:
                            if col.type.python_type == str:
                                match_kwargs[col.name] = "N/A"
                            elif col.type.python_type == int:
                                match_kwargs[col.name] = 0

                    match_obj = Match(**match_kwargs)
                    db.add(match_obj)
            except Exception as e:
                print(f"[ADMIN] Lỗi lưu bảng Match: {e}")

        db.commit()
        return {"status": "success", "message": "Cập nhật Cây thi đấu và Quán quân thành công!"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu CSDL: {str(e)}")