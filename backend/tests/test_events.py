import asyncio

from app.services.events import EventBroker


def test_event_broker_replays_events_after_cursor():
    async def scenario():
        broker = EventBroker()
        await broker.publish(9, {"type": "stage", "stage": "plan"})
        await broker.publish(9, {"type": "stage", "stage": "generate"})
        return await broker.replay(9, 1)

    replay = asyncio.run(scenario())
    assert [event["stage"] for event in replay] == ["generate"]
    assert replay[0]["event_id"] == 2
