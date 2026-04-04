"""Redis Streams helper untuk message queue antar agen."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Stream key constants
# ---------------------------------------------------------------------------

AGENT_EVENTS_STREAM = "agent:events"

# Consumer group names per agen
SELECTOR_GROUP = "selector-group"
SENDER_GROUP = "sender-group"
MONITOR_GROUP = "monitor-group"
CLASSIFIER_GROUP = "classifier-group"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


async def publish_event(
    redis_client: Any,
    stream_key: str,
    event_data: Dict[str, str],
) -> str:
    """Publish event ke Redis Streams via XADD.

    Args:
        redis_client: Instance async Redis client (e.g. redis.asyncio.Redis).
        stream_key: Nama stream yang dituju.
        event_data: Dict berisi field-value yang akan dipublikasikan.

    Returns:
        Message ID yang diberikan oleh Redis.
    """
    message_id: str = await redis_client.xadd(stream_key, event_data)
    return message_id


async def create_consumer_group(
    redis_client: Any,
    stream_key: str,
    consumer_group: str,
) -> None:
    """Buat consumer group pada stream jika belum ada.

    Menggunakan XGROUP CREATE dengan flag MKSTREAM agar stream dibuat
    otomatis jika belum ada. Jika group sudah ada, error diabaikan.

    Args:
        redis_client: Instance async Redis client.
        stream_key: Nama stream target.
        consumer_group: Nama consumer group yang akan dibuat.
    """
    try:
        await redis_client.xgroup_create(
            stream_key,
            consumer_group,
            id="0",
            mkstream=True,
        )
    except Exception as exc:  # noqa: BLE001
        # BUSYGROUP: consumer group sudah ada — abaikan
        if "BUSYGROUP" not in str(exc):
            raise


async def consume_events(
    redis_client: Any,
    stream_key: str,
    consumer_group: str,
    consumer_name: str,
    count: int = 10,
) -> List[Tuple[str, Dict[str, str]]]:
    """Consume events dari Redis Streams via XREADGROUP.

    Membaca pesan baru (ID ">") yang belum pernah dikirim ke consumer
    manapun dalam group ini.

    Args:
        redis_client: Instance async Redis client.
        stream_key: Nama stream yang dibaca.
        consumer_group: Nama consumer group.
        consumer_name: Nama consumer unik dalam group.
        count: Jumlah maksimum pesan yang dibaca sekaligus (default 10).

    Returns:
        List of (message_id, fields_dict). Mengembalikan list kosong jika
        tidak ada pesan baru.
    """
    results = await redis_client.xreadgroup(
        consumer_group,
        consumer_name,
        {stream_key: ">"},
        count=count,
    )

    messages: List[Tuple[str, Dict[str, str]]] = []
    if not results:
        return messages

    for _stream, entries in results:
        for message_id, fields in entries:
            messages.append((message_id, fields))

    return messages


async def acknowledge_event(
    redis_client: Any,
    stream_key: str,
    consumer_group: str,
    message_id: str,
) -> int:
    """Acknowledge event yang sudah diproses via XACK.

    Args:
        redis_client: Instance async Redis client.
        stream_key: Nama stream tempat pesan berada.
        consumer_group: Nama consumer group yang memproses pesan.
        message_id: ID pesan yang akan di-acknowledge.

    Returns:
        Jumlah pesan yang berhasil di-acknowledge (0 atau 1).
    """
    acked: int = await redis_client.xack(stream_key, consumer_group, message_id)
    return acked
