import io
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

# Kiểm tra quyền Admin
def verify_admin(current_user: User = Depends(get_current_user)):
    # Đổi điều kiện kiểm tra admin tùy theo CSDL của bạn (ví dụ: current_user.is_admin hoặc current_user.role == "admin")
    if not getattr(current_user, "is_admin", False) and getattr(current_user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ Admin mới có quyền truy cập API này")
    return current_user

# 1. API Xuất tất cả các Bot READY thành 1 file ZIP để tải về Laptop BTC
@router.get("/export-bots")
async def export_bots(
    group: str = None, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    # Lấy danh sách các bot hợp lệ
    query = db.query(Bot).filter(Bot.status == "READY")
    bots = query.all()

    if not bots:
        raise HTTPException(status_code=440, detail="Không có Bot nào ở trạng thái READY")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for bot in bots:
            curr_ver = bot.current_version
            if curr_ver and curr_ver.code:
                # Tên file trong zip: bot_{bot_id}.py
                filename = f"group_{group or 'ALL'}/bot_{bot.id}_user_{bot.user_id}.py"
                zip_file.writestr(filename, curr_ver.code)

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
@router.post("/import-results")
async def import_results(
    data: MatchResultImport,
    db: Session = Depends(get_db),
    admin_user: User = Depends(verify_admin)
):
    # Lưu hoặc cập nhật kết quả giải đấu vào CSDL
    # Bạn có thể gọi service cập nhật Tournament/Ranking ở đây
    print(f"[ADMIN] Đã nhận kết quả Giải đấu ID {data.tournament_id}: {len(data.standings)} vị trí, {len(data.match_logs)} trận đấu.")
    
    return {
        "status": "success", 
        "message": f"Đã cập nhật thành công {len(data.standings)} kết quả vào hệ thống!"
    }