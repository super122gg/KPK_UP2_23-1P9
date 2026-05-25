# Сервис 24: Room Availability Service (Сервис занятости аудиторий)

## Функционал сервиса
- Добавить RoomBlock
- Изменить RoomBlock по ID
- Удаление RoomBlock по ID
- Получить RoomBlock по ID
- Получить список RoomBlock по заданным параметрам

## Добавить RoomBlock
|Метод| Ссылка |
|---|---|
|`POST`|`/blocks/`|

Информация требуемая для создания RoomBlock представлена в виде таблицы со столбцами:

| Параметр | Пояснение | Обязательность | Тип | Ограничение | Значение по умолчанию |
|---|---|---|---|---|---|
| room_id | Идентификатор аудитории | Да | Integer | > 0 | - |
| event_id | Идентификатор события/причины блокировки | Да | Integer | > 0 | - |
| start_datetime | Дата и время начала блокировки | Да | DateTime | Не в прошлом | - |
| end_datetime | Дата и время окончания блокировки | Да | DateTime | > start_datetime | - |
| status_id | Идентификатор статуса (FK → Status) | Нет | Integer | > 0 | 1 |
| comment | Дополнительный комментарий | Нет | String | Макс. 500 символов | "" |
| is_deleted | Флаг удаления (soft delete) | Нет | Boolean | True/False | False |

Перечислить уникальные комбинации параметров, если есть:
Уникальная комбинация `(room_id, start_datetime, end_datetime)` не допускается. Временные интервалы для одной аудитории не должны пересекаться.

Информация возвращаемая в случае удачного создания RoomBlock представлена в виде таблицы со столбцами:

| Параметр | Тип |
|---|---|
| id | Integer |
| room_id | Integer |
| event_id | Integer |
| start_datetime | DateTime |
| end_datetime | DateTime |
| status_id | Integer |
| comment | String |
| is_deleted | Boolean |
| created_at | DateTime |

## Изменить RoomBlock по ID
|Метод| Ссылка |
|---|---|
| `PATCH` | `/blocks/{block_id}/` |

Информация требуемая для изменения RoomBlock по ID представлена в виде таблицы со столбцами:

| Параметр | Пояснение | Обязательность | Тип | Ограничение | Значение по умолчанию |
|---|---|---|---|---|---|
| block_id (в URL) | Идентификатор записи для изменения | Да | Integer | > 0 | - |
| start_datetime | Новая дата и время начала блокировки | Нет | DateTime | Не в прошлом | - |
| end_datetime | Новая дата и время окончания блокировки | Нет | DateTime | > start_datetime | - |
| status_id | Новый идентификатор статуса (FK → Status) | Нет | Integer | > 0 | - |
| comment | Новый комментарий | Нет | String | Макс. 500 символов | - |
| is_deleted | Флаг удаления (soft delete) | Нет | Boolean | True/False | - |

Информация возвращаемая в случае удачного изменения RoomBlock представлена в виде таблицы со столбцами:

| Параметр | Тип |
|---|---|
| id | Integer |
| room_id | Integer |
| event_id | Integer |
| start_datetime | DateTime |
| end_datetime | DateTime |
| status_id | Integer |
| comment | String |
| is_deleted | Boolean |
| updated_at | DateTime |

## Удаление RoomBlock по ID
|Метод| Ссылка |
|---|---|
| `DELETE` | `/blocks/{block_id}/` |

Вернет True, если RoomBlock была закрыта (удалена), иначе вернет False. Фактически запись из БД не удаляется, а реализуется через булевое поле is_deleted.

## Получить RoomBlock по ID
|Метод| Ссылка |
|---|---|
| `GET` | `/blocks/{block_id}` |

Информация возвращаемая в случае удачного поиска RoomBlock по ID представлена в виде таблицы со столбцами:

| Параметр | Пояснение | Тип |
|---|---|---|
| id | Идентификатор записи | Integer |
| room_id | Идентификатор аудитории | Integer |
| event_id | Идентификатор события/причины | Integer |
| start_datetime | Дата и время начала блокировки | DateTime |
| end_datetime | Дата и время окончания блокировки | DateTime |
| status_id | Идентификатор статуса | Integer |
| comment | Дополнительный комментарий | String |
| is_deleted | Флаг удаления (soft delete) | Boolean |
| created_at | Дата и время создания записи | DateTime |

## Получить список RoomBlock по заданным параметрам
|Метод| Ссылка |
|---|---|
| `GET` | `/blocks/` |

Информация требуемая для получения списка RoomBlock представлена в виде таблицы со столбцами:

| Параметр | Пояснение | Тип | Описание |
|---|---|---|---|
| room_id | Идентификатор аудитории | Integer | Фильтрация по ID аудитории |
| event_id | Идентификатор события/причины | Integer | Фильтрация по ID мероприятия |
| status_id | Идентификатор статуса | Integer | Фильтрация по ID статуса |
| date_from | Начало диапазона поиска | DateTime | Фильтрация по дате начала |
| date_to | Конец диапазона поиска | DateTime | Фильтрация по дате окончания |
| limit | Количество записей | Integer | Пагинация: максимум записей в ответе |
| offset | Смещение | Integer | Пагинация: количество пропускаемых записей |

Информация возвращается в виде списка RoomBlock и представлена в виде таблицы со столбцами:

| Параметр | Тип |
|---|---|
| id | Integer |
| room_id | Integer |
| event_id | Integer |
| start_datetime | DateTime |
| end_datetime | DateTime |
| status_id | Integer |
| comment | String |
| is_deleted | Boolean |
| created_at | DateTime |

## ER-диаграмма
![ER-диаграмма](erd.png)
