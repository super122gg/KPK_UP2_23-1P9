from peewee import *
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

db = SqliteDatabase('room_equipment.db')


class EquipmentType(str, Enum):
    TECH = "tech"
    FURNITURE = "furniture"
    TOOL = "tool"
    
    @classmethod
    def get_values(cls) -> List[str]:
        return [item.value for item in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.get_values()


class EnumCharField(CharField):
    def __init__(self, enum_class, *args, **kwargs):
        self.enum_class = enum_class
        kwargs['max_length'] = max(len(e.value) for e in enum_class)
        kwargs['choices'] = [(e.value, e.name) for e in enum_class]
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        if value not in self.enum_class.get_values():
            raise ValueError(f"Значение должно быть одним из: {self.enum_class.get_values()}")
        return super().validate(value)


class BaseModel(Model):
    class Meta:
        database = db


class Equipment(BaseModel):
    name = CharField(max_length=100, unique=True)
    description = CharField(max_length=500, null=True)
    equipment_type = EnumCharField(EquipmentType, default=EquipmentType.TECH.value)
    is_portable = BooleanField(default=False)
    power_required = BooleanField(default=False)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(null=True)

    class Meta:
        table_name = 'equipment'

    def save(self, *args, **kwargs):
        is_new = self.id is None
        
        if not self.name or not self.name.strip():
            raise ValueError("Название оборудования обязательно для заполнения")
        
        if is_new:
            if len(self.name) > 100:
                raise ValueError("Название оборудования должно содержать максимум 100 символов")
        else:
            if len(self.name) < 2 or len(self.name) > 100:
                raise ValueError("Название оборудования должно содержать от 2 до 100 символов")
        
        if is_new:
            exists = Equipment.select().where(Equipment.name == self.name).exists()
            if exists:
                raise ValueError(f"Оборудование с названием '{self.name}' уже существует")
        else:
            if self.dirty_fields and 'name' in self.dirty_fields:
                exists = Equipment.select().where(
                    (Equipment.name == self.name) & (Equipment.id != self.id)
                ).exists()
                if exists:
                    raise ValueError(f"Оборудование с названием '{self.name}' уже существует")
        
        if self.description is not None and len(self.description) > 500:
            raise ValueError("Описание должно содержать максимум 500 символов")
        

        if not is_new:
            dirty_fields = [f for f in self.dirty_fields if f != 'updated_at']
            if dirty_fields:
                self.updated_at = datetime.now()
        
        return super().save(*args, **kwargs)

    @classmethod
    def soft_delete_by_id(cls, equipment_id: int) -> bool:
        try:
            equipment = cls.get_by_id(equipment_id)
            if not equipment.is_active:
                return False
            equipment.is_active = False
            equipment.updated_at = datetime.now()
            equipment.save()
            return True
        except DoesNotExist:
            return False

    def soft_delete(self) -> bool:
        """Soft delete текущего экземпляра"""
        if not self.is_active:
            return False
        self.is_active = False
        self.updated_at = datetime.now()
        self.save()
        return True

    def restore(self) -> bool:
        if self.is_active:
            return False
        self.is_active = True
        self.updated_at = datetime.now()
        self.save()
        return True

    @classmethod
    def get_by_id_or_none(cls, equipment_id: int) -> Optional['Equipment']:
        try:
            return cls.get_by_id(equipment_id)
        except DoesNotExist:
            return None

    @classmethod
    def get_equipment_by_id(cls, equipment_id: int) -> Optional[Dict[str, Any]]:

        equipment = cls.get_by_id_or_none(equipment_id)
        if equipment is None:
            return None
        return equipment.to_dict(for_list=False)

    @classmethod
    def get_active_by_id(cls, equipment_id: int) -> Optional['Equipment']:
        try:
            return cls.get((cls.id == equipment_id) & (cls.is_active == True))
        except DoesNotExist:
            return None

    @classmethod
    def filter_equipment(cls,
                         equipment_type: Optional[str] = None,
                         is_portable: Optional[bool] = None,
                         power_required: Optional[bool] = None,
                         is_active: Optional[bool] = None,
                         search: Optional[str] = None,
                         limit: int = 20,
                         offset: int = 0) -> List['Equipment']:

        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit должен быть целым положительным числом")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("offset должен быть целым неотрицательным числом")
        
        query = cls.select()
        
        if equipment_type:
            if not EquipmentType.is_valid(equipment_type):
                raise ValueError(f"Неверный тип оборудования: {equipment_type}")
            query = query.where(cls.equipment_type == equipment_type)
        if is_portable is not None:
            query = query.where(cls.is_portable == is_portable)
        if power_required is not None:
            query = query.where(cls.power_required == power_required)
        if is_active is not None:
            query = query.where(cls.is_active == is_active)
        if search:
            query = query.where(cls.name.contains(search))
        
        query = query.limit(limit).offset(offset)
        
        return list(query)

    @classmethod
    def filter_equipment_dict(cls,
                              equipment_type: Optional[str] = None,
                              is_portable: Optional[bool] = None,
                              power_required: Optional[bool] = None,
                              is_active: Optional[bool] = None,
                              search: Optional[str] = None,
                              limit: int = 20,
                              offset: int = 0) -> List[Dict[str, Any]]:

        equipment_list = cls.filter_equipment(
            equipment_type=equipment_type,
            is_portable=is_portable,
            power_required=power_required,
            is_active=is_active,
            search=search,
            limit=limit,
            offset=offset
        )
        return [e.to_dict(for_list=True) for e in equipment_list]

    @classmethod
    def count_filtered(cls,
                       equipment_type: Optional[str] = None,
                       is_portable: Optional[bool] = None,
                       power_required: Optional[bool] = None,
                       is_active: Optional[bool] = None,
                       search: Optional[str] = None) -> int:
        query = cls.select()
        
        if equipment_type:
            if not EquipmentType.is_valid(equipment_type):
                raise ValueError(f"Неверный тип оборудования: {equipment_type}")
            query = query.where(cls.equipment_type == equipment_type)
        if is_portable is not None:
            query = query.where(cls.is_portable == is_portable)
        if power_required is not None:
            query = query.where(cls.power_required == power_required)
        if is_active is not None:
            query = query.where(cls.is_active == is_active)
        if search:
            query = query.where(cls.name.contains(search))
        
        return query.count()

    def to_dict(self, for_list: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "equipment_type": self.equipment_type,
            "is_portable": self.is_portable,
            "power_required": self.power_required,
            "is_active": self.is_active,
        }
        
        if not for_list:
            data["created_at"] = self.created_at.isoformat() if self.created_at else None
            data["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        
        return data


def init_db():
    db.connect()
    db.create_tables([Equipment])


if __name__ == '__main__':
    init_db()
