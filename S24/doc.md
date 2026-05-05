# Сервис 24: Room Availability Service (Сервис занятости аудиторий)

## Функционал сервиса
- Добавить RoomBlock
- Изменить RoomBlock по ID
- Удаление RoomBlock по ID
- Получить RoomBlock по ID
- Получить список RoomBlock по заданным параметрам

## Добавить RoomBlock
Информация требуемая для создания RoomBlock представлена в виде таблицы со столбцами:

| Параметр | Обязательность | Тип | Ограничение | Значение по умолчанию |
|---|---|---|---|---|
| room_id | Да | Integer | > 0 | - |
| event_id | Да | Integer | > 0 | - |
| start_datetime | Да | DateTime | Не в прошлом | - |
| end_datetime | Да | DateTime | > start_datetime | - |
| status | Нет | String | "active", "cancelled", "pending" | "active" |
| comment | Нет | String | Макс. 500 символов | "" |

Перечислить уникальные комбинации параметров, если есть:
Уникальная комбинация `(room_id, start_datetime, end_datetime)` не допускается. Блокировки могут накладываться только если временные интервалы не пересекаются.

Информация возвращаемая в случае удачного создания RoomBlock и представлена в виде таблицы со столбцами:

| Параметр | Тип |
|---|---|
| id | Integer |
| room_id | Integer |
| event_id | Integer |
| start_datetime | DateTime |
| end_datetime | DateTime |
| status | String |
| comment | String |
| created_at | DateTime |

## Изменить RoomBlock по ID
Информация требуемая для изменения RoomBlock по ID представлена в виде таблицы со столбцами:

| Параметр | Обязательность | Тип | Ограничение | Значение по умолчанию |
|---|---|---|---|---|
| id | Да | Integer | > 0 | - |
| start_datetime | Нет | DateTime | Не в прошлом | - |
| end_datetime | Нет | DateTime | > start_datetime | - |
| status | Нет | String | "active", "cancelled", "pending" | - |
| comment | Нет | String | Макс. 500 символов | - |

Информация возвращаемая в случае удачного изменения RoomBlock и представлена в виде таблицы со столбцами:

| Параметр | Тип |
|---|---|
| id | Integer |
| room_id | Integer |
| event_id | Integer |
| start_datetime | DateTime |
| end_datetime | DateTime |
| status | String |
| comment | String |
| updated_at | DateTime |

## Удаление RoomBlock по ID
Вернет True, если RoomBlock была закрыта (удалена), иначе вернет False.

## Получить RoomBlock по ID
Информация возвращаемая в случае удачного поиска RoomBlock по ID и представлена в виде таблицы со столбцами:

| Параметр | Тип |
|---|---|
| id | Integer |
| room_id | Integer |
| event_id | Integer |
| start_datetime | DateTime |
| end_datetime | DateTime |
| status | String |
| comment | String |
| created_at | DateTime |

## Получить список RoomBlock по заданным параметрам
Информация требуемая для получения списка RoomBlock представлена в виде таблицы со столбцами:

| Параметр | Тип | Описание |
|---|---|---|
| room_id | Integer | Фильтрация по ID аудитории |
| event_id | Integer | Фильтрация по ID мероприятия/причины |
| status | String | Фильтрация по статусу ("active", "cancelled") |
| date_from | Date | Начало диапазона поиска |
| date_to | Date | Конец диапазона поиска |
| limit | Integer | Количество записей в ответе (по умолчанию 50) |
| offset | Integer | Смещение для пагинации (по умолчанию 0) |

Информация возвращается в виде списка RoomBlock и представлена в виде таблицы со столбцами:

| Параметр | Тип |
|---|---|
| id | Integer |
| room_id | Integer |
| event_id | Integer |
| start_datetime | DateTime |
| end_datetime | DateTime |
| status | String |
| comment | String |
| created_at | DateTime |

## ER-диаграмма

