"""Independent asynchronous cursors over a SAGE EventJournal.

No subscriber-owned queue, producer cancellation, or event duplication is used.
The caller authorizes stream IDs and owns the journal/store lifetime. Close or
cancel all subscription tasks before closing that store. Cancellation drains an
in-flight blocking read before returning, including repeated cancellation.
"""

from __future__ import annotations

import asyncio
import math
import time


class EventSubscription:
    def __init__(self, journal, *, poll_interval=0.1, heartbeat_interval=15.0, page_size=100):
        for interval in (poll_interval, heartbeat_interval):
            if isinstance(interval, bool) or not math.isfinite(interval) or interval <= 0:
                raise ValueError("event_subscription_interval_must_be_positive")
        if type(page_size) is not int or page_size <= 0:
            raise ValueError("event_subscription_page_size_must_be_positive")
        self._journal = journal
        self._poll_interval = poll_interval
        self._heartbeat_interval = heartbeat_interval
        self._page_size = page_size

    async def _read(self, stream_id, cursor):
        task = asyncio.create_task(asyncio.to_thread(
            self._journal.read, stream_id, after=cursor, limit=self._page_size))
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                # Cancelling a to_thread future cannot stop its thread. Keep
                # ownership until the actual read finishes, not just its wrapper.
                cancelled = True
        if cancelled:
            # Retrieve an exception too; a cancelled subscriber must not leak an
            # unobserved task error or let a caller close active storage early.
            task.exception()
            raise asyncio.CancelledError
        return task.result()

    async def stream(self, stream_id, *, after=0):
        """Yield committed event dictionaries, or None for a heartbeat.

        `after` is the last event delivered to this subscriber. Reconnection may
        repeat an unacknowledged delivery; applications deduplicate by sequence.
        A terminal page ends only after all its events have been yielded.
        Empty streams may be subscribed before publication. Each iterator owns
        its cursor, including multiple iterators from one subscription object.
        """
        cursor = after
        last_delivery = time.monotonic()
        while True:
            page = await self._read(stream_id, cursor)
            for event in page["events"]:
                cursor = event["sequence"]
                last_delivery = time.monotonic()
                yield event
            if page["closed"] and page["caught_up"]:
                return
            if not page["caught_up"]:
                continue
            if time.monotonic() - last_delivery >= self._heartbeat_interval:
                last_delivery = time.monotonic()
                yield None
            await asyncio.sleep(self._poll_interval)
