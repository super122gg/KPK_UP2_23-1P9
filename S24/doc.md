# Сервис 24: Room Availability Service (Сервис занятости аудиторий)

Сервис хранит только данные своей предметной области: блокировки аудиторий (`RoomBlock`) и локальный справочник статусов (`Status`).  
Данные аудиторий и событий из других сервисов не дублируются: используются только внешние идентификаторы `room_id` и `event_id` как числа.

## Функционал сервиса
- Добавить `RoomBlock`
- Изменить `RoomBlock` по ID
- Удалить `RoomBlock` по ID (soft delete)
- Получить `RoomBlock` по ID
- Получить список `RoomBlock` по параметрам
 
## Добавить RoomBlock
| Метод | Ссылка |
|---|---|
| `POST` | `/blocks/` |

| Параметр | Пояснение | Обязательность | Тип | Ограничение | Значение по умолчанию |
|---|---|---|---|---|---|
| `room_id` | ID аудитории (внешний ID из Room Service) | Да | Integer | > 0 | - |
| `event_id` | ID события/причины (внешний ID) | Да | Integer | > 0 | - |
| `start_datetime` | Дата и время начала блокировки | Да | DateTime | Не в прошлом | - |
| `end_datetime` | Дата и время окончания блокировки | Да | DateTime | > `start_datetime` | - |
| `status_id` | ID статуса (`Status`) | Нет | Integer | > 0 | `1` |
| `comment` | Комментарий | Нет | String | длина <= 500 | `""` |

Уникальные комбинации:
- `(room_id, start_datetime, end_datetime)` уникальна.

Правила пересечений:
- интервалы одной аудитории не должны пересекаться;
- блоки со статусом `cancelled` (`status_id = 2`) в проверке пересечений не участвуют.

| Параметр | Тип |
|---|---|
| `id` | Integer |
| `room_id` | Integer |
| `event_id` | Integer |
| `start_datetime` | DateTime |
| `end_datetime` | DateTime |
| `status_id` | Integer |
| `comment` | String |
| `is_deleted` | Boolean |
| `created_at` | DateTime |
| `updated_at` | DateTime |

## Изменить RoomBlock по ID
| Метод | Ссылка |
|---|---|
| `PATCH` | `/blocks/{block_id}` |

| Параметр | Пояснение | Обязательность | Тип | Ограничение |
|---|---|---|---|---|
| `block_id` (в URL) | Идентификатор записи для изменения | Да | Integer | > 0 |
| `start_datetime` | Новое начало блокировки | Нет | DateTime | Не в прошлом |
| `end_datetime` | Новое окончание блокировки | Нет | DateTime | > `start_datetime` |
| `status_id` | Новый статус | Нет | Integer | > 0 |
| `comment` | Новый комментарий | Нет | String | длина <= 500 |
| `is_deleted` | Флаг soft delete | Нет | Boolean | `true/false` |

| Параметр | Тип |
|---|---|
| `id` | Integer |
| `room_id` | Integer |
| `event_id` | Integer |
| `start_datetime` | DateTime |
| `end_datetime` | DateTime |
| `status_id` | Integer |
| `comment` | String |
| `is_deleted` | Boolean |
| `created_at` | DateTime |
| `updated_at` | DateTime |

## Удаление RoomBlock по ID
| Метод | Ссылка |
|---|---|
| `DELETE` | `/blocks/{block_id}` |

HTTP-статус: `200`.

Возвращаемое значение:
- `true`, если запись была помечена удаленной;
- `false`, если запись не найдена или уже удалена.

Запись физически не удаляется, используется поле `is_deleted`.

## Получить RoomBlock по ID
| Метод | Ссылка |
|---|---|
| `GET` | `/blocks/{block_id}` |

| Параметр | Пояснение | Тип |
|---|---|---|
| `id` | Идентификатор записи | Integer |
| `room_id` | ID аудитории | Integer |
| `event_id` | ID события | Integer |
| `start_datetime` | Начало блокировки | DateTime |
| `end_datetime` | Окончание блокировки | DateTime |
| `status_id` | ID статуса | Integer |
| `comment` | Комментарий | String |
| `is_deleted` | Флаг soft delete | Boolean |
| `created_at` | Дата создания | DateTime |
| `updated_at` | Дата изменения | DateTime |

Удаленные записи (`is_deleted = true`) по этому эндпоинту не возвращаются (`404`).

## Получить список RoomBlock по заданным параметрам
| Метод | Ссылка |
|---|---|
| `GET` | `/blocks/` |

| Параметр | Пояснение | Тип |
|---|---|---|
| `room_id` | Фильтр по аудитории | Integer |
| `event_id` | Фильтр по событию | Integer |
| `status_id` | Фильтр по статусу | Integer |
| `date_from` | Левая граница периода | DateTime |
| `date_to` | Правая граница периода | DateTime |
| `limit` | Лимит (1..100) | Integer |
| `offset` | Смещение (>=0) | Integer |

| Параметр | Тип |
|---|---|
| `id` | Integer |
| `room_id` | Integer |
| `event_id` | Integer |
| `start_datetime` | DateTime |
| `end_datetime` | DateTime |
| `status_id` | Integer |
| `comment` | String |
| `is_deleted` | Boolean |
| `created_at` | DateTime |
| `updated_at` | DateTime |

## Коды ошибок
| HTTP | Условие |
|---|---|
| `400` | Некорректные даты (`start` в прошлом, `end <= start`) |
| `404` | Не найден `block_id` или `status_id` |
| `409` | Пересечение интервалов или дубликат `(room_id, start_datetime, end_datetime)` |

## Справочник Status (инициализация БД)
| id | name | description |
|---|---|---|
| 1 | active | Активная блокировка |
| 2 | cancelled | Отменённая блокировка |
| 3 | pending | Ожидает подтверждения |

## Точки входа REST API
| Метод | Эндпоинт | Описание |
|---|---|---|
| `POST` | `/blocks/` | Создать блокировку |
| `PATCH` | `/blocks/{block_id}` | Обновить блокировку |
| `DELETE` | `/blocks/{block_id}` | Удалить блокировку (soft delete) |
| `GET` | `/blocks/{block_id}` | Получить блокировку по ID |
| `GET` | `/blocks/` | Получить список блокировок |
| `GET` | `/health` | Проверка доступности сервиса |

## ER-диаграмма
ER-диаграмма представлена в файле `erd.png`:

![ER-диаграмма](erd.png)
