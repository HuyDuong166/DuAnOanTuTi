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

# Hàm hỗ trợ trích xuất mã nguồn linh hoạt từ đối tượng Bot / BotVersion
def get_code_from_object(obj):
    if not obj:
        return None
    # Danh sách các tên cột phổ biến chứa code hoặc đường dẫn file
    for attr in ["source_code", "code", "content", "script", "file_content", "file_path", "code_path"]:
        val = getattr(obj, attr, None)
        if val and isinstance(val, str):
            # Nếu giá trị là đường dẫn tới tệp tồn tại trên đĩa
            if os.path.exists(val) and os.path.isfile(val):
                try:
                    with open(val, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
            # Nếu là nội dung mã nguồn (chuỗi text)
            elif len(val.strip()) > 0:
                return val
    return None

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

            # 1. Thử lấy từ phiên bản hiện tại (current_version)
            curr_ver = getattr(bot, "current_version", None)
            code_content = get_code_from_object(curr_ver)

            # 2. Thử lấy từ chính đối tượng Bot
            if not code_content:
                code_content = get_code_from_object(bot)

            # 3. Thử truy vấn bản ghi BotVersion mới nhất trong CSDL
            if not code_content:
                latest_ver = db.query(BotVersion).filter(BotVersion.bot_id == bot.id).order_by(BotVersion.id.desc()).first()
                code_content = get_code_from_object(latest_ver)

            # Ghi vào file ZIP nếu tìm thấy mã nguồn
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