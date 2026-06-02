"""HTTP-клиент для Room Availability Service (только запросы к API, не сервер)."""

import json
import os
import sys
from datetime import datetime, timedelta

try:
    import httpx
except ImportError:
    print("Установите httpx: pip install httpx")
    sys.exit(1)

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


def _print(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))

def create_block(client: httpx.Client, room_id: int, event_id: int,
                 start: datetime, end: datetime, status_id: int = 1, comment: str = ""):
    response = client.post(f"{BASE_URL}/blocks/", json={
        "room_id": room_id,
        "event_id": event_id,
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "status_id": status_id,
        "comment": comment,
    })
    response.raise_for_status()
    return response.json()


def get_block(client: httpx.Client, block_id: int):
    response = client.get(f"{BASE_URL}/blocks/{block_id}")
    response.raise_for_status()
    return response.json()


def list_blocks(client: httpx.Client, **params):
    response = client.get(f"{BASE_URL}/blocks/", params=params)
    response.raise_for_status()
    return response.json()


def update_block(client: httpx.Client, block_id: int, **fields):
    response = client.patch(f"{BASE_URL}/blocks/{block_id}", json=fields)
    response.raise_for_status()
    return response.json()


def delete_block(client: httpx.Client, block_id: int):
    response = client.delete(f"{BASE_URL}/blocks/{block_id}")
    response.raise_for_status()
    return response.json()


def main():
    try:
        with httpx.Client(timeout=10.0) as client:
            try:
                health = client.get(f"{BASE_URL}/health")
                health.raise_for_status()
            except httpx.ConnectError:
                print(
                    f"Не удалось подключиться к {BASE_URL}\n"
                    "Сначала запустите сервер в отдельном терминале:\n"
                    "  uvicorn service:app --reload"
                )
                sys.exit(1)
            except httpx.HTTPStatusError as exc:
                print(
                    f"Сервер вернул ошибку {exc.response.status_code} на {BASE_URL}/health\n"
                    "Убедитесь, что на порту 8000 запущен именно этот сервис:\n"
                    "  uvicorn service:app --reload\n"
                    "Если порт занят другим приложением, укажите другой:\n"
                    "  uvicorn service:app --port 8001"
                )
                sys.exit(1)

            print("Сервис доступен:", health.json())
            room_id = 101
            event_id = 501

            start = datetime.now() + timedelta(hours=1)
            end = start + timedelta(hours=2)
            block = create_block(client, room_id, event_id, start, end, comment="Покраска")
            print("\nСоздана блокировка:")
            _print(block)

            block_id = block["id"]
            print("\nПолучение блокировки по ID:")
            _print(get_block(client, block_id))

            print("\nСписок блокировок (status_id=1):")
            _print(list_blocks(client, status_id=1, room_id=room_id))

            new_end = end + timedelta(hours=1)
            print("\nОбновление блокировки:")
            _print(update_block(client, block_id, end_datetime=new_end.isoformat(), comment="Продлено"))

            print("\nУдаление блокировки (soft delete):")
            _print(delete_block(client, block_id))

            print("\nПовторное удаление (ожидается False):")
            _print(delete_block(client, block_id))

            start2 = datetime.now() + timedelta(hours=3)
            end2 = start2 + timedelta(hours=1)
            cancelled = create_block(
                client, room_id, event_id, start2, end2,
                status_id=2, comment="Отменённая",
            )
            print("\nОтменённая блокировка (status_id=2):")
            _print(cancelled)
            start3 = start2 + timedelta(minutes=15)
            end3 = end2 + timedelta(minutes=15)
            active_overlap = create_block(
                client, room_id, event_id, start3, end3,
                status_id=1, comment="Активная, пересекается по времени",
            )
            print("\nАктивная блокировка с пересечением (ожидается успех — cancelled не учитывается):")
            _print(active_overlap)
    except httpx.HTTPStatusError as exc:
        print(f"Ошибка API {exc.response.status_code}: {exc.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
