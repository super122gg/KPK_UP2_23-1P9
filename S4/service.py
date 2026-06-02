from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from peewee import IntegrityError, fn
import httpx
from models import db, Permission, RolePermission, init_db

ROLE_SERVICE_URL = "http://localhost:8001" 

class PermissionCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field('', max_length=255)


class PermissionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class PermissionOut(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool

    class Config:
        from_attributes = True


class RolePermissionCreate(BaseModel):
    role_id: int
    permission_id: int


class RolePermissionOut(BaseModel):
    id: int
    role_id: int
    permission_id: int


class DeleteResponse(BaseModel):
    deleted: bool


class ErrorResponse(BaseModel):
    detail: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    if not db.is_closed():
        db.close()


app = FastAPI(title="Permission Service", lifespan=lifespan)


@app.post("/permissions", response_model=PermissionOut, status_code=201)
def create_permission(perm: PermissionCreate):
    try:
        with db.atomic():
            return Permission.create(
                name=perm.name,
                description=perm.description
            )
    except IntegrityError:
        raise HTTPException(400, "Разрешение с таким названием уже существует. Название должно быть уникальным.")


@app.get("/permissions/{perm_id}", response_model=PermissionOut)
def get_permission(perm_id: int):
    perm = Permission.get_or_none(Permission.id == perm_id)
    if not perm:
        raise HTTPException(404, "Разрешение не найдено")
    return perm


@app.get("/permissions", response_model=List[PermissionOut])
def list_permissions(
    name: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    query = Permission.select()
    if name:
        query = query.where(fn.LOWER(Permission.name).contains(name.lower()))
    if is_active is not None:
        query = query.where(Permission.is_active == is_active)
    return list(query.offset(offset).limit(limit))


@app.put("/permissions/{perm_id}", response_model=PermissionOut)
def update_permission(perm_id: int, perm: PermissionUpdate):
    existing = Permission.get_or_none(Permission.id == perm_id)
    if not existing:
        raise HTTPException(404, "Разрешение не найдено")

    update_data = {k: v for k, v in perm.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(400, "Нет данных для обновления")

    try:
        with db.atomic():
            Permission.update(update_data).where(Permission.id == perm_id).execute()
        return Permission.get_by_id(perm_id)
    except IntegrityError:
        raise HTTPException(400, "Название уже занято другим разрешением. Название должно быть уникальным.")


@app.delete("/permissions/{perm_id}", response_model=DeleteResponse)
def delete_permission(perm_id: int):
    updated = Permission.update(is_active=False).where(Permission.id == perm_id).execute()
    return DeleteResponse(deleted=bool(updated))


@app.post("/role-permissions", response_model=RolePermissionOut, status_code=201)
def create_role_permission(rp: RolePermissionCreate):
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{ROLE_SERVICE_URL}/roles/{rp.role_id}")
            if response.status_code == 404:
                raise HTTPException(404, f"Роль с id={rp.role_id} не найдена в Role Service")
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(503, "Role Service недоступен")
    except httpx.RequestError:
        raise HTTPException(503, "Ошибка подключения к Role Service")

    permission = Permission.get_or_none((Permission.id == rp.permission_id) & (Permission.is_active == True))
    if not permission:
        raise HTTPException(404, f"Разрешение с id={rp.permission_id} не найдено")

    try:
        with db.atomic():
            return RolePermission.create(role_id=rp.role_id, permission_id=rp.permission_id)
    except IntegrityError:
        raise HTTPException(400, "Такая связь уже существует")


@app.get("/role-permissions", response_model=List[RolePermissionOut])
def list_role_permissions(
    role_id: Optional[int] = Query(None),
    permission_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    query = RolePermission.select()
    if role_id is not None:
        query = query.where(RolePermission.role_id == role_id)
    if permission_id is not None:
        query = query.where(RolePermission.permission_id == permission_id)
    return list(query.offset(offset).limit(limit))


@app.get("/role-permissions/{rp_id}", response_model=RolePermissionOut)
def get_role_permission(rp_id: int):
    rp = RolePermission.get_or_none(RolePermission.id == rp_id)
    if not rp:
        raise HTTPException(404, "Связь не найдена")
    return rp


@app.put("/role-permissions/{rp_id}", response_model=ErrorResponse, status_code=405)
def update_role_permission(rp_id: int):
    raise HTTPException(405, "Для транзитивной таблицы изменение не предусмотрено. Для изменения связи необходимо удалить существующую и создать новую.")


@app.delete("/role-permissions/{rp_id}", response_model=DeleteResponse)
def delete_link_by_id(rp_id: int):
    deleted = RolePermission.delete().where(RolePermission.id == rp_id).execute()
    return DeleteResponse(deleted=bool(deleted))


@app.delete("/role-permissions", response_model=DeleteResponse)
def delete_role_permission_by_params(
    role_id: int = Query(...), 
    permission_id: int = Query(...)
):
    deleted = RolePermission.delete().where(
        (RolePermission.role_id == role_id) & (RolePermission.permission_id == permission_id)
    ).execute()
    return DeleteResponse(deleted=bool(deleted))


@app.get("/role-permissions/by-role/{role_id}", response_model=List[PermissionOut])
def get_permissions_by_role(role_id: int):
    return list(
        Permission.select()
        .join(RolePermission)
        .where(RolePermission.role_id == role_id)
    )


@app.get("/")
def root():
    return {
        "service": "Permission Service",
        "version": "1.0",
        "endpoints": {
            "POST /permissions": "Создать разрешение",
            "GET /permissions/{id}": "Получить разрешение по ID",
            "GET /permissions": "Список разрешений с фильтрацией",
            "PUT /permissions/{id}": "Обновить разрешение",
            "DELETE /permissions/{id}": "Удалить разрешение (soft delete)",
            "POST /role-permissions": "Создать связь роли и разрешения",
            "GET /role-permissions/{id}": "Получить связь по ID",
            "GET /role-permissions": "Получить список связей с фильтрацией",
            "PUT /role-permissions/{id}": "Изменить связь (не предусмотрено)",
            "DELETE /role-permissions/{id}": "Удалить связь по ID (hard delete)",
            "DELETE /role-permissions": "Удалить связь по параметрам (role_id, permission_id)",
            "GET /role-permissions/by-role/{role_id}": "Получить все разрешения для роли"
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Запуск Permission Service...")
    print("Документация API: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000)
