from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from models import Department, init_db, db, validate_phone, validate_email, validate_code, validate_cabinet_id


# ==================== Pydantic схемы с валидацией ====================

class DepartmentCreate(BaseModel):
    name: str
    code: str
    head_name: str
    head_specialty: Optional[str] = None
    head_phone: Optional[str] = None
    head_email: Optional[str] = None
    head_cabinet_id: Optional[int] = None
    reception_is_active: bool = False
    reception_schedule: Optional[str] = None

    @field_validator('name')
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError('Название должно быть не менее 2 символов')
        return v

    @field_validator('code')
    def validate_code_field(cls, v):
        if len(v) < 2:
            raise ValueError('Код должен быть не менее 2 символов')
        if not validate_code(v):
            raise ValueError('Код должен быть в формате 09.02.07')
        return v

    @field_validator('head_name')
    def validate_head_name(cls, v):
        if len(v) < 2:
            raise ValueError('ФИО заведующего должно быть не менее 2 символов')
        return v

    @field_validator('head_specialty')
    def validate_head_specialty(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError('Специальность должна быть не менее 2 символов')
        return v

    @field_validator('head_phone')
    def validate_head_phone(cls, v):
        if v is not None and not validate_phone(v):
            raise ValueError('Телефон должен быть в формате +7XXXXXXXXXX')
        return v

    @field_validator('head_email')
    def validate_head_email(cls, v):
        if v is not None and not validate_email(v):
            raise ValueError('Неверный формат email')
        return v

    @field_validator('head_cabinet_id')
    def validate_head_cabinet(cls, v):
        if v is not None and not validate_cabinet_id(v):
            raise ValueError('Номер кабинета должен быть положительным числом')
        return v


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    head_name: Optional[str] = None
    head_specialty: Optional[str] = None
    head_phone: Optional[str] = None
    head_email: Optional[str] = None
    head_cabinet_id: Optional[int] = None
    reception_is_active: Optional[bool] = None
    reception_schedule: Optional[str] = None

    @field_validator('name')
    def validate_name(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError('Название должно быть не менее 2 символов')
        return v

    @field_validator('code')
    def validate_code_field(cls, v):
        if v is not None:
            if len(v) < 2:
                raise ValueError('Код должен быть не менее 2 символов')
            if not validate_code(v):
                raise ValueError('Код должен быть в формате 09.02.07')
        return v

    @field_validator('head_name')
    def validate_head_name(cls, v):
        if v is not None and len(v) < 2:
            raise ValueError('ФИО заведующего должно быть не менее 2 символов')
        return v

    @field_validator('head_phone')
    def validate_head_phone(cls, v):
        if v is not None and not validate_phone(v):
            raise ValueError('Телефон должен быть в формате +7XXXXXXXXXX')
        return v

    @field_validator('head_email')
    def validate_head_email(cls, v):
        if v is not None and not validate_email(v):
            raise ValueError('Неверный формат email')
        return v

    @field_validator('head_cabinet_id')
    def validate_head_cabinet(cls, v):
        if v is not None and not validate_cabinet_id(v):
            raise ValueError('Номер кабинета должен быть положительным числом')
        return v


class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str
    head_name: str
    head_specialty: Optional[str] = None
    head_phone: Optional[str] = None
    head_email: Optional[str] = None
    head_cabinet_id: Optional[int] = None
    reception_is_active: bool
    reception_schedule: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== FastAPI ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Запуск сервера Faculty Service...")
    init_db()
    print("База данных инициализирована")
    yield
    print("Остановка сервера...")
    if not db.is_closed():
        db.close()
    print("Ресурсы освобождены")

app = FastAPI(
    title="Faculty Service",
    description="Сервис управления отделениями СПО",
    version="1.0",
    lifespan=lifespan
)


@app.post("/departments", response_model=DepartmentOut, status_code=201)
def create_department(dept: DepartmentCreate):
    db.connect()

    try:
        new_dept = Department.create(
            name=dept.name,
            code=dept.code,
            head_name=dept.head_name,
            head_specialty=dept.head_specialty,
            head_phone=dept.head_phone,
            head_email=dept.head_email,
            head_cabinet_id=dept.head_cabinet_id,
            reception_is_active=dept.reception_is_active,
            reception_schedule=dept.reception_schedule
        )
        db.close()
        return new_dept
    except Exception as e:
        db.close()
        if "UNIQUE" in str(e):
            raise HTTPException(400, "Отделение с таким названием и кодом уже существует")
        raise HTTPException(400, str(e))


@app.get("/departments/{dept_id}", response_model=DepartmentOut)
def get_department(dept_id: int):
    db.connect()
    try:
        dept = Department.get_by_id(dept_id)
        return dept
    except Department.DoesNotExist:
        raise HTTPException(404, "Отделение не найдено")
    finally:
        db.close()


@app.get("/departments", response_model=List[DepartmentOut])
def list_departments(name: Optional[str] = None, limit: int = 100):
    db.connect()
    query = Department.select()
    if name:
        query = query.where(Department.name.contains(name))
    result = list(query.limit(limit))
    db.close()
    return result


@app.put("/departments/{dept_id}", response_model=DepartmentOut)
def update_department(dept_id: int, dept: DepartmentUpdate):
    db.connect()
    if not Department.select().where(Department.id == dept_id).exists():
        db.close()
        raise HTTPException(404, "Отделение не найдено")
    
    update_data = dept.model_dump(exclude_unset=True)
    if update_data:
        try:
            Department.update(update_data).where(Department.id == dept_id).execute()
        except Exception as e:
            db.close()
            if "UNIQUE" in str(e):
                raise HTTPException(400, "Отделение с таким названием и кодом уже существует")
            raise HTTPException(400, str(e))
    
    updated = Department.get_by_id(dept_id)
    db.close()
    return updated


@app.delete("/departments/{dept_id}")
def delete_department(dept_id: int):
    db.connect()
    deleted = Department.delete().where(Department.id == dept_id).execute()
    db.close()
    return {"deleted": bool(deleted)}


@app.get("/")
def root():
    return {
        "service": "Faculty Service",
        "version": "1.0",
        "endpoints": {
            "POST /departments": "Создать отделение",
            "GET /departments": "Список отделений",
            "GET /departments/{id}": "Получить по ID",
            "PUT /departments/{id}": "Обновить",
            "DELETE /departments/{id}": "Удалить"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Запуск сервера Faculty Service...")
    print("Документация API: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000)