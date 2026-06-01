# S14 — Load Calculation Service (Сервис расчета нагрузки преподавателя)

---

#### Добавить нагрузку

Информация, требуемая для создания нагрузки:

| Параметр | Пояснение | Обязательность | Тип | Ограничение | Значение по умолчанию |
|----------|-----------|----------------|-----|-------------|----------------------|
| teacher_id | ID преподавателя | Обязательно | integer | внешний ключ → Profile Service | — |
| discipline_id | ID дисциплины | Обязательно | integer | внешний ключ → Discipline Service | — |
| hours_per_week | Часов в неделю | Обязательно | float | от 1 до 54 | — |
| groups_count | Количество групп | Обязательно | integer | от 1 до 10 | — |
| semester | Номер семестра | Обязательно | integer | 1 или 2 | — |
| year | Учебный год | Обязательно | integer | от 2020 до 2030 | — |
| notes | Примечания | Опционально | string | до 500 символов | null |

**Уникальные комбинации параметров:**
- `(teacher_id, discipline_id, semester, year)` — один преподаватель не может вести одну дисциплину дважды в одном семестре.

Формула расчёта: `total_hours = hours_per_week × groups_count × 18`

Информация, возвращаемая при успешном создании:

| Параметр | Тип |
|----------|-----|
| id | integer |
| teacher_id | integer |
| discipline_id | integer |
| hours_per_week | float |
| groups_count | integer |
| semester | integer |
| year | integer |
| total_hours | float |
| notes | string или null |
| is_active | boolean |

---

#### Изменить нагрузку по ID

Информация, требуемая для изменения (все поля необязательны):

| Параметр | Пояснение | Обязательность | Тип | Ограничение | Значение по умолчанию |
|----------|-----------|----------------|-----|-------------|----------------------|
| hours_per_week | Новое кол-во часов в неделю | Опционально | float | от 1 до 54 | текущее значение |
| groups_count | Новое кол-во групп | Опционально | integer | от 1 до 10 | текущее значение |
| notes | Новые примечания | Опционально | string | до 500 символов | текущее значение |

> Поля `teacher_id`, `discipline_id`, `semester`, `year` изменить нельзя. При изменении `hours_per_week` или `groups_count` поле `total_hours` пересчитывается автоматически по формуле `hours_per_week × groups_count × 18`.

Информация, возвращаемая при успешном изменении:

| Параметр | Тип |
|----------|-----|
| id | integer |
| teacher_id | integer |
| discipline_id | integer |
| hours_per_week | float |
| groups_count | integer |
| semester | integer |
| year | integer |
| total_hours | float |
| notes | string или null |
| is_active | boolean |

---

#### Удалить нагрузку по ID

Вернёт `true`, если нагрузка была деактивирована (`is_active = false`), иначе `false`. Физически запись из БД не удаляется.

---

#### Получить нагрузку по ID

| Параметр | Пояснение | Тип |
|----------|-----------|-----|
| id | Уникальный идентификатор | integer |
| teacher_id | ID преподавателя | integer |
| discipline_id | ID дисциплины | integer |
| hours_per_week | Часов в неделю | float |
| groups_count | Количество групп | integer |
| semester | Номер семестра | integer |
| year | Учебный год | integer |
| total_hours | Общая нагрузка за семестр | float |
| notes | Примечания | string или null |
| is_active | Активна ли запись | boolean |

---

#### Получить список нагрузок по заданным параметрам

| Параметр | Пояснение | Тип | Ограничение |
|----------|-----------|-----|-------------|
| teacher_id | Фильтр по преподавателю | integer | |
| discipline_id | Фильтр по дисциплине | integer | |
| semester | Фильтр по семестру | integer | 1 или 2 |
| year | Фильтр по году | integer | от 2020 до 2030 |
| min_hours | Минимум часов в неделю | float | |
| max_hours | Максимум часов в неделю | float | |
| min_total | Минимальная общая нагрузка | float | |
| max_total | Максимальная общая нагрузка | float | |
| limit | Количество записей | integer | от 1 до 100 |
| offset | Смещение | integer | ≥ 0 |

Информация возвращается в виде списка нагрузок, каждая содержит:

| Параметр | Тип |
|----------|-----|
| id | integer |
| teacher_id | integer |
| discipline_id | integer |
| hours_per_week | float |
| groups_count | integer |
| semester | integer |
| year | integer |
| total_hours | float |
| notes | string или null |
| is_active | boolean |

---

## ER-диаграмма

![ER-диаграмма](erd.png)