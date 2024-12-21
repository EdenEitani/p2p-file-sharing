import unittest
import asyncio
from connection_limiter import ConnectionLimiter

class TestConnectionLimiter(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    async def mock_connection(self, limiter, delay=0.1):
        async with limiter.semaphore:
            await asyncio.sleep(delay)
            return True

    def test_connection_limit(self):
        limiter = ConnectionLimiter(max_connections=2)
        start_time = self.loop.time()
        
        async def run_test():
            results = await asyncio.gather(
                self.mock_connection(limiter),
                self.mock_connection(limiter),
                self.mock_connection(limiter)
            )
            return results, self.loop.time() - start_time

        results, elapsed = self.loop.run_until_complete(run_test())
        self.assertGreaterEqual(elapsed, 0.2)  # Third connection should wait
        self.assertTrue(all(results))

    def test_connection_overflow(self):
        limiter = ConnectionLimiter(max_connections=1)
        
        async def timed_connection():
            start = self.loop.time()
            await self.mock_connection(limiter, delay=0.1)
            return self.loop.time() - start

        async def run_test():
            return await asyncio.gather(
                timed_connection(),
                timed_connection(),
                timed_connection()
            )

        times = self.loop.run_until_complete(run_test())
        self.assertGreaterEqual(times[1], 0.1)
        self.assertGreaterEqual(times[2], 0.2)

    def test_connection_release(self):
        limiter = ConnectionLimiter(max_connections=1)
        
        async def fail_connection():
            try:
                async with limiter.semaphore:
                    raise Exception("Test error")
            except:
                pass

        self.loop.run_until_complete(fail_connection())
        self.assertEqual(limiter.semaphore._value, 1)

if __name__ == '__main__':
    unittest.main()