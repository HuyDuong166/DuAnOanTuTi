import io
import os
import zipfile
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import inspect
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
        print(f"[EXPORT ERROR] Lỗi đọc TournamentParticipant: {e}")

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


@router.post("/import-results")
async def import_results(
    data: MatchResultImport,
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    try:
        # 1. Cập nhật điểm số cho Bot & User
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

        winner_info = "Chưa cập nhật"
        matches_created_count = 0

        # 2. Cập nhật trạng thái Giải Đấu & Nhà Vô Địch (Dynamic Mapping)
        if data.tournament_id:
            from backend.models.tournament import Tournament
            tournament = db.query(Tournament).filter(Tournament.id == data.tournament_id).first()
            if tournament:
                tour_cols = [c.key for c in inspect(Tournament).column_attrs]
                
                if "status" in tour_cols:
                    tournament.status = "COMPLETED"

                if data.standings:
                    winner_bot_id = data.standings[0].get("bot_id")
                    winner_bot = db.query(Bot).filter(Bot.id == winner_bot_id).first()
                    winner_user_id = getattr(winner_bot, "user_id", None) if winner_bot else None

                    if "winner_bot_id" in tour_cols:
                        tournament.winner_bot_id = winner_bot_id
                    if "winner_user_id" in tour_cols:
                        tournament.winner_user_id = winner_user_id
                    if "winner_id" in tour_cols:
                        tournament.winner_id = winner_user_id or winner_bot_id
                    if "winner" in tour_cols and not isinstance(getattr(Tournament, "winner", None), property):
                        try:
                            setattr(tournament, "winner", winner_user_id or winner_bot_id)
                        except Exception:
                            pass

                    winner_info = f"Bot ID {winner_bot_id} (User ID {winner_user_id})"

        # 3. Lưu danh sách Trận Đấu (Match) vào CSDL (Dynamic Mapping)
        if data.match_logs:
            Match = None
            try:
                from backend.models.match import Match
            except ImportError:
                try:
                    from backend.models.tournament import Match
                except ImportError:
                    pass

            if Match:
                try:
                    db.query(Match).filter(Match.tournament_id == data.tournament_id).delete(synchronize_session=False)
                except Exception as e:
                    print(f"[IMPORT MATCH WARNING] Xóa trận cũ: {e}")

                match_cols = [c.key for c in inspect(Match).column_attrs]

                for idx, m in enumerate(data.match_logs, start=1):
                    match_kwargs = {}

                    if "tournament_id" in match_cols:
                        match_kwargs["tournament_id"] = data.tournament_id

                    b1 = m.get("bot1_id")
                    for col in ["bot1_id", "player1_id", "bot_1_id", "user1_id"]:
                        if col in match_cols:
                            match_kwargs[col] = b1
                            break

                    b2 = m.get("bot2_id")
                    for col in ["bot2_id", "player2_id", "bot_2_id", "user2_id"]:
                        if col in match_cols:
                            match_kwargs[col] = b2
                            break

                    w_id = m.get("winner_id")
                    for col in ["winner_id", "winner_bot_id", "winner_user_id"]:
                        if col in match_cols:
                            match_kwargs[col] = w_id
                            break

                    r_num = m.get("round", 1)
                    for col in ["round", "round_num", "round_number", "stage_round"]:
                        if col in match_cols:
                            match_kwargs[col] = r_num
                            break

                    for col in ["status", "state"]:
                        if col in match_cols:
                            match_kwargs[col] = "COMPLETED"
                            break

                    log_val = str(m.get("log", ""))
                    for col in ["log", "logs", "detail", "details"]:
                        if col in match_cols:
                            match_kwargs[col] = log_val
                            break

                    for col in ["match_number", "order", "number"]:
                        if col in match_cols:
                            match_kwargs[col] = idx
                            break

                    # Điền giá trị mặc định tránh lỗi NOT NULL
                    for column in Match.__table__.columns:
                        if not column.nullable and column.default is None and not column.primary_key and not column.autoincrement and column.name not in match_kwargs:
                            if column.type.python_type == str:
                                match_kwargs[column.name] = "COMPLETED"
                            elif column.type.python_type == int:
                                match_kwargs[column.name] = 0

                    match_obj = Match(**match_kwargs)
                    db.add(match_obj)
                    matches_created_count += 1

        db.commit()
        return {
            "status": "success",
            "message": f"Đã lưu thành công {matches_created_count} trận đấu và cập nhật Quán quân!",
            "winner": winner_info,
            "matches_created": matches_created_count
        }

    except Exception as e:
        db.rollback()
        print(f"[IMPORT ERROR] Lỗi khi lưu CSDL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu CSDL: {str(e)}")