# Сервис 24: Room Availability Service (Сервис занятости аудиторий)

## Функционал сервиса
- Добавить RoomBlock
- Изменить RoomBlock по ID
- Удаление RoomBlock по ID (soft delete)
- Получить RoomBlock по ID
- Получить список RoomBlock по заданным параметрам

## Добавить RoomBlock
Информация требуемая для создания RoomBlock представлена в виде таблицы со столбцами:

| Параметр | Пояснение | Обязательность | Тип | Ограничение | Значение по умолчанию |
|---|---|---|---|---|---|
| room_id | Идентификатор аудитории | Да | Integer | > 0 | - |
| event_id | Идентификатор события/причины блокировки | Да | Integer | > 0 | - |
| start_datetime | Дата и время начала блокировки | Да | DateTime | Не в прошлом | - |
| end_datetime | Дата и время окончания блокировки | Да | DateTime | > start_datetime | - |
| status | Статус блокировки | Нет | String | "active", "cancelled", "pending" | "active" |
| comment | Дополнительный комментарий | Нет | String | Макс. 500 символов | "" |

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

| Параметр | Пояснение | Обязательность | Тип | Ограничение | Значение по умолчанию |
|---|---|---|---|---|---|
| id | Идентификатор записи для изменения | Да | Integer | > 0 | - |
| start_datetime | Новая дата и время начала блокировки | Нет | DateTime | Не в прошлом | - |
| end_datetime | Новая дата и время окончания блокировки | Нет | DateTime | > start_datetime | - |
| status | Новый статус блокировки | Нет | String | "active", "cancelled", "pending" | - |
| comment | Новый комментарий | Нет | String | Макс. 500 символов | - |

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
**Примечание:** Фактически запись из БД не удаляется, а реализуется через булевое поле `is_deleted`.

## Получить RoomBlock по ID
Информация возвращаемая в случае удачного поиска RoomBlock по ID и представлена в виде таблицы со столбцами:

| Параметр | Пояснение | Тип |
|---|---|---|
| id | Идентификатор записи | Integer |
| room_id | Идентификатор аудитории | Integer |
| event_id | Идентификатор события/причины | Integer |
| start_datetime | Дата и время начала блокировки | DateTime |
| end_datetime | Дата и время окончания блокировки | DateTime |
| status | Статус блокировки | String |
| comment | Дополнительный комментарий | String |
| created_at | Дата и время создания записи | DateTime |

## Получить список RoomBlock по заданным параметрам
Информация требуемая для получения списка RoomBlock представлена в виде таблицы со столбцами:

| Параметр | Пояснение | Тип | Описание |
|---|---|---|---|
| room_id | Идентификатор аудитории | Integer | Фильтрация по ID аудитории |
| event_id | Идентификатор события/причины | Integer | Фильтрация по ID мероприятия |
| status | Статус блокировки | String | Фильтрация по статусу ("active", "cancelled") |
| date_from | Начало диапазона поиска | Date | Фильтрация по дате начала |
| date_to | Конец диапазона поиска | Date | Фильтрация по дате окончания |
| limit | Количество записей | Integer | Количество записей в ответе |
| offset | Смещение | Integer | Смещение для пагинации |

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
![Scrinshot](https://github.com/super122gg/KPK_UP2_23-1P9/blob/main/S24/ERD.png)
