"""Log pressure and slow/cross-thread clients; no HTTP server or game device."""
import asyncio
from threading import Event
import unittest

from starlette.websockets import WebSocketState

from module.server.script_websocket import ScriptWSManager
from module.server.worker_log import BufferedLogSender


class BufferedLogTest(unittest.TestCase):
    def test_full_live_log_queue_does_not_block_producer_or_shutdown(self):
        entered, release = Event(), Event()
        delivered = []

        def send(message):
            entered.set()
            release.wait()
            delivered.append(message)

        sender = BufferedLogSender(send, capacity=2)
        try:
            sender('first')
            self.assertTrue(entered.wait(1))
            # The transport cannot make progress; callers still return and
            # the bounded buffer retains only the most recent live records.
            for index in range(1000):
                sender(str(index))
            self.assertEqual(sender.queue.qsize(), 2)
            sender.close(timeout=0.01)
            self.assertTrue(sender.thread.is_alive())
        finally:
            release.set()
            sender.close(timeout=1)
        self.assertFalse(sender.thread.is_alive())
        self.assertEqual(delivered, ['first', '998', '999'])

    def test_broken_live_pipe_disables_delivery_without_raising_into_task(self):
        failed = Event()

        def send(message):
            failed.set()
            raise BrokenPipeError('closed monitor')

        sender = BufferedLogSender(send)
        try:
            sender('first')
            self.assertTrue(failed.wait(1))
            sender.thread.join(1)
            self.assertTrue(sender.closed.is_set())
            for _ in range(1000):
                sender('task continues')
            self.assertEqual(sender.queue.qsize(), 0)
        finally:
            sender.close()


class FakeSocket:
    def __init__(self, slow=False):
        self.client_state = WebSocketState.CONNECTED
        self.slow = slow
        self.received = []
        self.sent = asyncio.Event()
        self.inflight = 0
        self.max_inflight = 0
        self.owner = asyncio.get_running_loop()

    async def accept(self):
        pass

    async def send_text(self, payload):
        if asyncio.get_running_loop() is not self.owner:
            raise AssertionError('ASGI send used from the wrong event loop')
        self.inflight += 1
        self.max_inflight = max(self.max_inflight, self.inflight)
        try:
            if self.slow:
                await asyncio.Event().wait()
            await asyncio.sleep(0)
            self.received.append(payload)
            self.sent.set()
        finally:
            self.inflight -= 1

    send_json = send_text

    async def close(self):
        if self.slow:
            await asyncio.Event().wait()
        self.client_state = WebSocketState.DISCONNECTED


class WebSocketDeliveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_slow_client_does_not_hold_up_fast_client_and_is_removed(self):
        manager = ScriptWSManager()
        manager.send_timeout = manager.close_timeout = 0.05
        slow, fast = FakeSocket(slow=True), FakeSocket()
        await manager.connect(slow)
        await manager.connect(fast)
        delivery = asyncio.create_task(manager.broadcast_log('task log'))
        await asyncio.wait_for(fast.sent.wait(), timeout=1)
        self.assertFalse(delivery.done())
        await asyncio.wait_for(delivery, timeout=1)
        self.assertEqual(manager.active_connections, [fast])
        self.assertNotIn(slow, manager._connection_owners)
        await manager.broadcast_state({'state': 1})
        self.assertEqual(fast.received, ['task log', {'state': 1}])

    async def test_background_log_and_http_state_send_on_owner_loop_serially(self):
        manager, socket = ScriptWSManager(), FakeSocket()
        await manager.connect(socket)
        await asyncio.gather(
            asyncio.to_thread(lambda: asyncio.run(manager.broadcast_log('background log'))),
            manager.broadcast_state({'state': 1}))
        self.assertEqual(socket.max_inflight, 1)
        self.assertEqual(len(socket.received), 2)
        self.assertIn('background log', socket.received)
        self.assertIn({'state': 1}, socket.received)
        await manager.disconnect(socket)
        self.assertFalse(manager.active_connections)


if __name__ == '__main__':
    unittest.main()
