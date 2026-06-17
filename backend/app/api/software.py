from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import os
import hashlib
import aiofiles
from pathlib import Path

from ..core.database import get_db
from ..core.deps import get_current_active_user, get_optional_current_user, require_ops, require_admin
from ..core.config import settings, get_max_upload_size, get_storage_path
from ..core.validators import sanitize_filename, validate_path_within_dir, ALLOWED_UPLOAD_EXTENSIONS
from ..models.user import User
from ..models.software import Software, SoftwareVersion
from ..models.vulnerability import Vulnerability
from ..models.request import SoftwareRequest
from ..schemas.software import (
    SoftwareCreate, SoftwareUpdate, SoftwareResponse,
    SoftwareVersionCreate, SoftwareVersionResponse, SoftwareListResponse, SoftwareListWithTotal, VersionInfo
)

router = APIRouter(prefix="/software", tags=["软件管理"])


def get_file_hash(file_path: str) -> str:
    """计算文件 SHA256 哈希"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@router.get("", response_model=SoftwareListWithTotal)
async def list_software(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """获取软件列表（支持游客访问）"""
    query = db.query(Software)

    if category:
        query = query.filter(Software.category == category)
    if search:
        query = query.filter(Software.name.contains(search))

    # 获取总数（在应用过滤条件后）
    total = query.count()

    # 获取分页数据，按更新时间降序排序
    software_list = query.order_by(Software.updated_at.desc()).offset(skip).limit(limit).all()

    result = []
    for sw in software_list:
        latest_version = db.query(SoftwareVersion)\
            .filter(SoftwareVersion.software_id == sw.id)\
            .order_by(SoftwareVersion.upload_time.desc())\
            .first()

        versions = db.query(SoftwareVersion).filter(SoftwareVersion.software_id == sw.id).all()
        total_downloads = sum(v.download_count for v in versions)

        result.append(SoftwareListResponse(
            id=sw.id,
            name=sw.name,
            description=sw.description,
            category=sw.category,
            icon_url=sw.icon_url,
            logo=sw.logo,
            official_url=sw.official_url,
            require_login=sw.require_login if sw.require_login is not None else True,
            screenshot_url_1=sw.screenshot_url_1,
            screenshot_url_2=sw.screenshot_url_2,
            screenshot_url_3=sw.screenshot_url_3,
            latest_version=latest_version.version if latest_version else None,
            version_count=len(versions),
            total_downloads=total_downloads
        ))

    return SoftwareListWithTotal(total=total, items=result)


# Specific routes must be defined before parameterized routes
@router.get("/categories", response_model=List[str])
async def get_categories(current_user: Optional[User] = Depends(get_optional_current_user), db: Session = Depends(get_db)):
    """获取软件分类列表（支持游客访问）"""
    categories = db.query(Software.category)\
        .filter(Software.category.isnot(None))\
        .distinct()\
        .all()
    return [c[0] for c in categories if c[0]]


@router.get("/{software_id}", response_model=SoftwareResponse)
async def get_software(software_id: int, current_user: Optional[User] = Depends(get_optional_current_user), db: Session = Depends(get_db)):
    """获取软件详情（支持游客访问）"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    # 获取版本信息
    versions = db.query(SoftwareVersion).filter(SoftwareVersion.software_id == software_id).all()

    return SoftwareResponse(
        id=software.id,
        name=software.name,
        description=software.description,
        category=software.category,
        icon_url=software.icon_url,
        logo=software.logo,
        official_url=software.official_url,
        require_login=software.require_login if software.require_login is not None else True,
        screenshot_url_1=software.screenshot_url_1,
        screenshot_url_2=software.screenshot_url_2,
        screenshot_url_3=software.screenshot_url_3,
        created_at=software.created_at,
        updated_at=software.updated_at,
        versions=[VersionInfo(
            id=v.id,
            version=v.version,
            file_name=v.file_name,
            file_size=v.file_size,
            file_hash=v.file_hash,
            upload_time=v.upload_time,
            download_count=v.download_count,
            release_notes=v.release_notes,
            original_download_url=v.original_download_url  # 从版本表直接读取
        ) for v in versions]
    )


@router.post("", response_model=SoftwareResponse, status_code=status.HTTP_201_CREATED)
async def create_software(
    software_data: SoftwareCreate,
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """创建软件"""
    # 检查软件名是否存在
    existing = db.query(Software).filter(Software.name == software_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="软件名称已存在")

    # 处理URL字段，将空字符串转换为None
    icon_url = str(software_data.icon_url) if software_data.icon_url else None
    logo = str(software_data.logo) if software_data.logo else None
    official_url = str(software_data.official_url) if software_data.official_url else None

    software = Software(
        name=software_data.name,
        description=software_data.description,
        category=software_data.category,
        icon_url=icon_url,
        logo=logo,
        official_url=official_url,
        require_login=software_data.require_login if software_data.require_login is not None else True,
        created_by=current_user.id
    )
    db.add(software)
    db.commit()
    db.refresh(software)

    return SoftwareResponse(
        id=software.id,
        name=software.name,
        description=software.description,
        category=software.category,
        icon_url=software.icon_url,
        logo=software.logo,
        official_url=software.official_url,
        require_login=software.require_login if software.require_login is not None else True,
        screenshot_url_1=software.screenshot_url_1,
        screenshot_url_2=software.screenshot_url_2,
        screenshot_url_3=software.screenshot_url_3,
        created_at=software.created_at,
        updated_at=software.updated_at,
        versions=[]
    )


@router.put("/{software_id}", response_model=SoftwareResponse)
async def update_software(
    software_id: int,
    software_data: SoftwareUpdate,
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """更新软件"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    # 检查软件名是否被其他软件占用
    if software_data.name and software_data.name != software.name:
        existing = db.query(Software).filter(Software.name == software_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="软件名称已存在")

    if software_data.name:
        software.name = software_data.name
    if software_data.description is not None:
        software.description = software_data.description
    if software_data.category is not None:
        software.category = software_data.category

    # 处理URL字段，将空字符串转换为None
    if software_data.icon_url is not None:
        software.icon_url = str(software_data.icon_url) if software_data.icon_url else None
    if software_data.logo is not None:
        software.logo = str(software_data.logo) if software_data.logo else None
    if software_data.official_url is not None:
        software.official_url = str(software_data.official_url) if software_data.official_url else None
    if software_data.require_login is not None:
        software.require_login = software_data.require_login

    db.commit()
    db.refresh(software)

    versions = db.query(SoftwareVersion)\
        .filter(SoftwareVersion.software_id == software_id)\
        .order_by(SoftwareVersion.upload_time.desc())\
        .all()

    return SoftwareResponse(
        id=software.id,
        name=software.name,
        description=software.description,
        category=software.category,
        icon_url=software.icon_url,
        logo=software.logo,
        official_url=software.official_url,
        require_login=software.require_login if software.require_login is not None else True,
        screenshot_url_1=software.screenshot_url_1,
        screenshot_url_2=software.screenshot_url_2,
        screenshot_url_3=software.screenshot_url_3,
        created_at=software.created_at,
        updated_at=software.updated_at,
        versions=[VersionInfo(
            id=v.id,
            version=v.version,
            file_name=v.file_name,
            file_size=v.file_size,
            file_hash=v.file_hash,
            upload_time=v.upload_time,
            download_count=v.download_count,
            release_notes=v.release_notes,
            original_download_url=v.original_download_url  # 从版本表直接读取
        ) for v in versions]
    )


@router.delete("/{software_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_software(
    software_id: int,
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """删除软件"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    # 删除所有版本文件
    from ..models.download import DownloadLog
    versions = db.query(SoftwareVersion).filter(SoftwareVersion.software_id == software_id).all()
    # 先删除关联的下载日志
    if versions:
        version_ids = [v.id for v in versions]
        db.query(DownloadLog).filter(DownloadLog.software_version_id.in_(version_ids)).delete(synchronize_session='fetch')
    for version in versions:
        if os.path.exists(version.file_path):
            os.remove(version.file_path)
        db.delete(version)

    db.delete(software)
    db.commit()

    return None


@router.post("/{software_id}/versions", response_model=SoftwareVersionResponse)
async def upload_version(
    software_id: int,
    version: str = Form(...),
    file: Optional[UploadFile] = File(None),
    release_notes: Optional[str] = Form(None),
    external_url: Optional[str] = Form(None),
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """上传软件版本（支持文件上传或外部下载地址）"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    # 必须提供文件或外部下载地址之一
    if not file and not (external_url and external_url.strip()):
        raise HTTPException(status_code=400, detail="请提供文件或外部下载地址")

    file_path = ""
    safe_filename = ""
    file_size = 0
    file_hash = ""

    if file:
        # 模式1：上传文件
        # 检查文件扩展名
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ''
        if file_ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，允许的类型: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            )

        # 流式写入文件，避免一次性加载大文件到内存
        safe_filename = sanitize_filename(file.filename)
        storage_path = get_storage_path(db)
        software_dir = os.path.join(storage_path, str(software_id))
        os.makedirs(software_dir, exist_ok=True)
        file_path = validate_path_within_dir(os.path.join(software_dir, safe_filename), storage_path)

        sha256_hash = hashlib.sha256()
        chunk_size = 1024 * 1024  # 1MB chunks
        async with aiofiles.open(file_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > get_max_upload_size(db):
                    await f.close()
                    os.remove(file_path)
                    raise HTTPException(status_code=400, detail="文件大小超过限制")
                sha256_hash.update(chunk)
                await f.write(chunk)
        file_hash = sha256_hash.hexdigest()
    else:
        # 模式2：外部下载地址
        # 如果未填写，使用软件的官网地址作为fallback
        actual_url = external_url.strip() if external_url else ""
        if not actual_url:
            actual_url = software.official_url or ""
        safe_filename = f"external_link_{version}.txt"
        file_path = ""  # 外部链接无需存储路径
        file_size = 0
        file_hash = ""

    # 创建版本记录
    software_version = SoftwareVersion(
        software_id=software_id,
        version=version,
        file_path=file_path,
        file_name=safe_filename,
        file_size=file_size,
        file_hash=file_hash,
        uploader_id=current_user.id,
        release_notes=release_notes,
        original_download_url=(external_url.strip() if (external_url and external_url.strip()) else None) or (software.official_url if not file else None)
    )
    # 如果是文件模式但没有显式 external_url，确保 original_download_url 为 None
    if file and not (external_url and external_url.strip()):
        software_version.original_download_url = None
    # 如果是外部地址模式但用户没填，fallback 到官网地址
    if not file and not (external_url and external_url.strip()):
        software_version.original_download_url = software.official_url or None

    db.add(software_version)
    db.commit()
    db.refresh(software_version)

    return SoftwareVersionResponse(
        id=software_version.id,
        software_id=software_version.software_id,
        version=software_version.version,
        file_name=software_version.file_name,
        file_size=software_version.file_size,
        file_hash=software_version.file_hash,
        upload_time=software_version.upload_time,
        download_count=software_version.download_count,
        release_notes=software_version.release_notes,
        software_name=software.name
    )


@router.post("/{software_id}/screenshots")
async def upload_screenshot(
    software_id: int,
    slot: int = Form(..., ge=1, le=3),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """上传/设置软件界面图（slot 1/2/3）"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    if not file and not (url and url.strip()):
        raise HTTPException(status_code=400, detail="请提供文件或图片URL")

    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
    max_size = 5 * 1024 * 1024  # 5MB

    # 文件模式
    if file:
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ''
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图片类型: {file_ext}，允许的类型: {', '.join(sorted(allowed_extensions))}"
            )

        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="图片大小不能超过5MB")

        import uuid
        unique_filename = f"{software_id}_s{slot}_{uuid.uuid4().hex[:8]}{file_ext}"
        storage_path = get_storage_path(db)
        screenshot_dir = os.path.join(storage_path, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        file_path = os.path.join(screenshot_dir, unique_filename)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # 删除该槽位旧的本地文件（如果旧值是本地路径）
        old_url = getattr(software, f"screenshot_url_{slot}")
        if old_url and old_url.startswith("/api/software/"):
            old_filename = old_url.split("/")[-1]
            old_path = os.path.join(screenshot_dir, old_filename)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

        new_url = f"/api/software/{software_id}/screenshots/file/{unique_filename}"
        setattr(software, f"screenshot_url_{slot}", new_url)
        db.commit()

        return {
            "screenshot_url": new_url,
            "slot": slot,
            "message": "截图上传成功"
        }

    # URL 模式
    url_value = url.strip()
    old_url = getattr(software, f"screenshot_url_{slot}")
    if old_url and old_url.startswith("/api/software/"):
        old_filename = old_url.split("/")[-1]
        storage_path = get_storage_path(db)
        old_path = os.path.join(storage_path, "screenshots", old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    setattr(software, f"screenshot_url_{slot}", url_value)
    db.commit()

    return {
        "screenshot_url": url_value,
        "slot": slot,
        "message": "截图URL设置成功"
    }


@router.delete("/{software_id}/screenshots/{slot}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_screenshot(
    software_id: int,
    slot: int,
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """删除软件界面图（slot 1/2/3）"""
    if slot not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="slot 必须是 1/2/3")

    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    old_url = getattr(software, f"screenshot_url_{slot}")
    if old_url and old_url.startswith("/api/software/"):
        old_filename = old_url.split("/")[-1]
        storage_path = get_storage_path(db)
        screenshot_dir = os.path.join(storage_path, "screenshots")
        old_path = os.path.join(screenshot_dir, old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    setattr(software, f"screenshot_url_{slot}", None)
    db.commit()

    return None


@router.post("/{software_id}/logo", response_model=dict)
async def upload_logo(
    software_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """上传软件Logo"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    # 检查文件类型（只允许图片）
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico'}
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ''
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="只支持上传图片文件（png, jpg, jpeg, gif, svg, webp, ico）")

    # 检查文件大小（限制5MB）
    content = await file.read()
    file_size = len(content)
    max_logo_size = 5 * 1024 * 1024  # 5MB
    if file_size > max_logo_size:
        raise HTTPException(status_code=400, detail="Logo文件大小不能超过5MB")

    # 创建logo目录
    storage_path = get_storage_path(db)
    logo_dir = os.path.join(storage_path, "logos")
    os.makedirs(logo_dir, exist_ok=True)

    # 生成唯一的文件名
    import uuid
    file_extension = file_ext
    unique_filename = f"{software_id}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = os.path.join(logo_dir, unique_filename)

    # 保存文件
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # 删除旧的logo文件
    if software.logo and software.logo.startswith("/api/software/"):
        old_logo_path = os.path.join(storage_path, "logos", os.path.basename(software.logo))
        if os.path.exists(old_logo_path):
            try:
                os.remove(old_logo_path)
            except:
                pass

    # 更新软件的logo字段
    software.logo = f"/api/software/{software_id}/logo/file/{unique_filename}"
    db.commit()

    return {
        "logo": software.logo,
        "message": "Logo上传成功"
    }


@router.get("/{software_id}/logo/file/{filename}")
async def get_logo_file(
    software_id: int,
    filename: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """获取logo文件（支持游客访问）"""
    from fastapi.responses import FileResponse

    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    safe_name = sanitize_filename(filename)
    storage_path = get_storage_path(db)
    logo_dir = os.path.join(storage_path, "logos")
    file_path = validate_path_within_dir(os.path.join(logo_dir, safe_name), logo_dir)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Logo文件不存在")

    return FileResponse(file_path)


@router.get("/logos/{filename}")
async def get_logo_file_direct(filename: str, current_user: Optional[User] = Depends(get_optional_current_user), db: Session = Depends(get_db)):
    """直接获取logo文件（不需要 software_id，支持游客访问）"""
    from fastapi.responses import FileResponse

    safe_name = sanitize_filename(filename)
    storage_path = get_storage_path(db)
    logo_dir = os.path.join(storage_path, "logos")
    file_path = validate_path_within_dir(os.path.join(logo_dir, safe_name), logo_dir)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Logo文件不存在")

    return FileResponse(file_path)


@router.get("/{software_id}/screenshots/file/{filename}")
async def get_screenshot_file(
    software_id: int,
    filename: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """获取界面图文件（支持游客访问）"""
    from fastapi.responses import FileResponse

    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    safe_name = sanitize_filename(filename)
    storage_path = get_storage_path(db)
    screenshot_dir = os.path.join(storage_path, "screenshots")
    file_path = validate_path_within_dir(os.path.join(screenshot_dir, safe_name), screenshot_dir)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="截图文件不存在")

    return FileResponse(file_path)


@router.put("/{software_id}/versions/{version_id}", response_model=SoftwareVersionResponse)
async def update_version(
    software_id: int,
    version_id: int,
    version: Optional[str] = Form(None),
    release_notes: Optional[str] = Form(None),
    external_url: Optional[str] = Form(None),
    file_name: Optional[str] = Form(None),  # 新增：手动指定文件名
    file_size: Optional[int] = Form(None),  # 新增：手动指定文件大小（字节）
    file: Optional[UploadFile] = File(None),
    delete_file: bool = Form(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """编辑软件版本（仅 admin）"""
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    ver = db.query(SoftwareVersion).filter(
        SoftwareVersion.id == version_id,
        SoftwareVersion.software_id == software_id
    ).first()
    if not ver:
        raise HTTPException(status_code=404, detail="版本不存在")

    # 如果修改了版本号，检查唯一性
    if version and version != ver.version:
        existing = db.query(SoftwareVersion).filter(
            SoftwareVersion.software_id == software_id,
            SoftwareVersion.version == version,
            SoftwareVersion.id != version_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="版本号已被其他版本占用")
        ver.version = version

    # 更新 release_notes
    if release_notes is not None:
        ver.release_notes = release_notes

    # 处理文件
    if file:
        # 上传新文件：覆盖原文件
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ''
        if file_ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，允许的类型: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            )

        safe_filename = sanitize_filename(file.filename)
        storage_path = get_storage_path(db)
        software_dir = os.path.join(storage_path, str(software_id))
        os.makedirs(software_dir, exist_ok=True)
        file_path = validate_path_within_dir(os.path.join(software_dir, safe_filename), storage_path)

        sha256_hash = hashlib.sha256()
        file_size_actual = 0
        chunk_size = 1024 * 1024
        async with aiofiles.open(file_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size_actual += len(chunk)
                if file_size_actual > get_max_upload_size(db):
                    await f.close()
                    os.remove(file_path)
                    raise HTTPException(status_code=400, detail="文件大小超过限制")
                sha256_hash.update(chunk)
                await f.write(chunk)

        ver.file_path = file_path
        # 如果用户手动提供了 file_name，使用手动值；否则用 sanitize 后的文件名
        ver.file_name = file_name.strip() if (file_name and file_name.strip()) else safe_filename
        # 如果用户手动提供了 file_size，使用手动值；否则用实际计算的大小
        ver.file_size = file_size if file_size is not None else file_size_actual
        ver.file_hash = sha256_hash.hexdigest()
    elif delete_file and ver.file_path:
        # 显式删除文件
        try:
            if os.path.exists(ver.file_path):
                os.remove(ver.file_path)
        except Exception:
            pass
        ver.file_path = ""
        ver.file_name = ""
        ver.file_size = 0
        ver.file_hash = ""
    else:
        # 没有上传新文件也没有删除文件：仅修改元数据
        if file_name is not None and file_name.strip():
            ver.file_name = file_name.strip()
        if file_size is not None:
            ver.file_size = file_size

    # 更新 external_url
    if external_url is not None:
        url_value = external_url.strip() if external_url.strip() else None
        ver.original_download_url = url_value

    db.commit()
    db.refresh(ver)

    return SoftwareVersionResponse(
        id=ver.id,
        software_id=ver.software_id,
        version=ver.version,
        file_name=ver.file_name,
        file_size=ver.file_size,
        file_hash=ver.file_hash,
        upload_time=ver.upload_time,
        download_count=ver.download_count,
        release_notes=ver.release_notes,
        software_name=software.name
    )


@router.delete("/{software_id}/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_software_version(
    software_id: int,
    version_id: int,
    current_user: User = Depends(require_ops),
    db: Session = Depends(get_db)
):
    """删除软件版本"""
    # 验证软件是否存在
    software = db.query(Software).filter(Software.id == software_id).first()
    if not software:
        raise HTTPException(status_code=404, detail="软件不存在")

    # 查找版本
    version = db.query(SoftwareVersion).filter(
        SoftwareVersion.id == version_id,
        SoftwareVersion.software_id == software_id
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    # 先删除关联的下载日志
    from ..models.download import DownloadLog
    db.query(DownloadLog).filter(DownloadLog.software_version_id == version_id).delete()

    # 删除文件
    if os.path.exists(version.file_path):
        try:
            os.remove(version.file_path)
        except Exception as e:
            # 文件删除失败不影响数据库记录的删除
            pass

    # 删除数据库记录
    db.delete(version)
    db.commit()

    return None