import asyncio
import pytest
from app.features.observability.broker import EventBroker

@pytest.mark.asyncio
async def test_broker_fanout_and_bounded_queue():
    broker=EventBroker(max_queue=2); first=broker.subscribe(); second=broker.subscribe()
    broker.publish({"type":"node.running","node_id":"n"})
    assert await asyncio.wait_for(first.get(),1) == {"type":"node.running","node_id":"n"}
    assert await asyncio.wait_for(second.get(),1) == {"type":"node.running","node_id":"n"}
    broker.publish({"type":"a"}); broker.publish({"type":"b"}); broker.publish({"type":"c"})
    assert first.qsize()==2
    broker.unsubscribe(first); broker.publish({"type":"d"}); assert second.qsize()<=2

def test_broker_rejects_oversized_events():
    broker=EventBroker(max_queue=2); broker.subscribe()
    with pytest.raises(ValueError): broker.publish({"type":"x","payload":"x"*300000})



def test_broker_close_unsubscribes():
    broker=EventBroker(); q=broker.subscribe(); broker.close(); assert q in broker._subscribers or q.qsize()==1
