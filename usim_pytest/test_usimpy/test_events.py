import pytest


from .utility import via_usimpy


class TestEvent:
    @via_usimpy
    def test_event_lifetime(self, env):
        event = env.event()
        assert not event.triggered
        assert not event.processed
        assert not event.ok
        event.succeed()
        assert event.triggered
        assert not event.processed
        assert event.ok
        yield event
        assert event.triggered
        assert event.processed
        assert event.ok
