import asyncio
from threading import Event

import pytest

from sage.runtime.event_journal import EventJournal
from sage.runtime.event_subscription import EventSubscription
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime


def test_independent_cursors_reconnect_and_terminal_pagination(tmp_path):
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "events.db"))
    journal = EventJournal(store, namespace="events")
    subscription = EventSubscription(journal, page_size=1)
    try:
        for i in range(3):
            journal.append("stream", event_id=str(i), payload=i, terminal=i == 2)

        async def run():
            first, second = subscription.stream("stream"), subscription.stream("stream")
            assert (await anext(first))["sequence"] == 1
            assert (await anext(second))["sequence"] == 1
            await first.aclose()
            assert [event["sequence"] async for event in second] == [2, 3]
            assert [event["sequence"] async for event in subscription.stream("stream", after=1)] == [2, 3]
            assert [event async for event in subscription.stream("stream", after=3)] == []
            with pytest.raises(ValueError, match="event_cursor_ahead"):
                await anext(subscription.stream("stream", after=4))
        asyncio.run(run())
    finally:
        store.close()


def test_heartbeat_then_separate_connection_publication(tmp_path):
    path = str(tmp_path / "events.db")
    reader = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    writer = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    journal = EventJournal(reader, namespace="events")
    publisher = EventJournal(writer, namespace="events")
    try:
        async def run():
            stream = EventSubscription(journal, poll_interval=0.001, heartbeat_interval=0.003).stream("stream")
            assert await asyncio.wait_for(anext(stream), 1) is None
            publisher.append("stream", event_id="done", payload="durable", terminal=True)
            assert (await asyncio.wait_for(anext(stream), 1))["payload"] == "durable"
            with pytest.raises(StopAsyncIteration):
                await anext(stream)
        asyncio.run(run())
    finally:
        reader.close()
        writer.close()


def test_repeated_cancellation_drains_actual_read():
    entered, release, finished = Event(), Event(), Event()
    class Journal:
        def read(self, *args, **kwargs):
            entered.set()
            assert release.wait(3)
            finished.set()
            return {"events": [], "closed": False, "caught_up": True}

    async def run():
        stream = EventSubscription(Journal()).stream("stream")
        task = asyncio.create_task(anext(stream))
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            task.cancel()
            await asyncio.sleep(0.01)
            task.cancel()
            await asyncio.sleep(0.01)
            assert not task.done()
            assert not finished.is_set()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert finished.is_set()
        finally:
            release.set()
            await stream.aclose()
    asyncio.run(run())


@pytest.mark.parametrize("options", [
    {"poll_interval": 0}, {"heartbeat_interval": float("nan")},
    {"poll_interval": True}, {"page_size": True}, {"page_size": -1},
])
def test_invalid_configuration(options):
    with pytest.raises(ValueError):
        EventSubscription(None, **options)
