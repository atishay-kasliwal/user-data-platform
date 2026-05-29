"""
Audit Logging Service — Kafka consumer that writes every read/write event
to stdout (production: stream to S3 via Firehose or Fluentd).

Consumed topics:
  - user.created
  - user.updated
  - user.accessed
  - user.consent_granted
  - user.consent_revoked
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI

app = FastAPI(title="Audit Logging Service", version="1.0.0")

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
TOPICS = [
    "user.created",
    "user.updated",
    "user.accessed",
    "user.consent_granted",
    "user.consent_revoked",
]

async def consume():
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BROKERS,
        group_id="audit-logging-service",
        auto_offset_reset="earliest",
        value_deserializer=lambda b: json.loads(b.decode()),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            entry = {
                "audit_at":  datetime.now(timezone.utc).isoformat(),
                "topic":     msg.topic,
                "partition": msg.partition,
                "offset":    msg.offset,
                "event":     msg.value,
            }
            # In production: write to S3 (Parquet) via Kinesis Firehose or Fluentd.
            # For now, write structured JSON to stdout (captured by log aggregator).
            print(json.dumps(entry, default=str), flush=True)
    finally:
        await consumer.stop()

@app.on_event("startup")
async def startup():
    asyncio.create_task(consume())

@app.get("/health")
async def health():
    return {"status": "ok"}
