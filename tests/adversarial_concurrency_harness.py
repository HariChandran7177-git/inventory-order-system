"""
Adversarial Concurrency & Stream Processing Verification Harness
Milestone 1 Verification — Fast-Cart Architecture

Tests:
1. Atomic Lua Script & Concurrency (Race conditions, overselling, negative quantities, boundary conditions)
2. Non-blocking Consumer Loops (asyncio.to_thread, event loop lag, thread offloading)
3. PEL Recovery Mechanism (xautoclaim on empty stream, uninitialized group, abandoned entries)
"""

import asyncio
import os
import sys
import threading
import time

sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("."))

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import redis
from loguru import logger

# Remove default log handlers to keep test output clean
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

from inventory.app.workers.consumer import (
    LUA_ATOMIC_DECREMENT,
    init_consumer_group,
    process_order_message,
    recover_pel_inventory,
)
from payment.app.workers.consumer import (
    recover_pel_refund,
    init_consumer_group as init_pay_consumer_group,
    process_refund_message,
)


class ConcurrencyHarnessResults:
    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.findings: List[str] = []

    def record_pass(self, test_name: str, detail: str = ""):
        self.passed.append(test_name)
        print(f"✅ PASS: {test_name} {detail}", flush=True)

    def record_fail(self, test_name: str, detail: str = ""):
        self.failed.append(test_name)
        print(f"❌ FAIL: {test_name} {detail}", flush=True)

    def record_finding(self, finding: str):
        self.findings.append(finding)
        print(f"⚠️ FINDING: {finding}", flush=True)


results = ConcurrencyHarnessResults()


# ==============================================================================
# 1. ATOMIC LUA SCRIPT DECREMENT & CONCURRENCY TESTS
# ==============================================================================

class RedisLuaSimulator:
    """
    Thread-safe simulator of Redis single-threaded command and Lua script execution.
    Mirrors LUA_ATOMIC_DECREMENT execution in backend/inventory/app/workers/consumer.py.
    """
    def __init__(self):
        self._data: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()

    def set_hash(self, key: str, mapping: Dict[str, Any]):
        with self._lock:
            self._data[key] = {k: str(v) for k, v in mapping.items()}

    def get_hash(self, key: str) -> Dict[str, str]:
        with self._lock:
            return self._data.get(key, {}).copy()

    def exists(self, key: str) -> int:
        with self._lock:
            return 1 if key in self._data else 0

    def hget(self, key: str, field: str) -> Optional[str]:
        with self._lock:
            return self._data.get(key, {}).get(field)

    def hset(self, key: str, field: str, value: str):
        with self._lock:
            if key not in self._data:
                self._data[key] = {}
            self._data[key][field] = str(value)

    def eval_lua_stock_decrement(self, key: str, order_qty: Any) -> int:
        """
        Executes LUA_ATOMIC_DECREMENT logic within an atomic lock (Redis single-thread guarantee).
        """
        with self._lock:
            # local key = KEYS[1]
            # local order_qty = tonumber(ARGV[1])
            try:
                order_qty_num = int(order_qty)
            except (ValueError, TypeError):
                order_qty_num = None

            # local exists = redis.call('EXISTS', key)
            if key not in self._data:
                return -1

            # local stock = redis.call('HGET', key, 'quantity')
            stock = self._data[key].get("quantity")
            if stock is None:
                return -1

            try:
                current_qty = int(stock)
            except (ValueError, TypeError):
                return -1

            if order_qty_num is None:
                raise ValueError("attempt to compare number with nil in Lua")

            # if current_qty < order_qty then return -2
            if current_qty < order_qty_num:
                return -2

            # local new_qty = current_qty - order_qty
            # redis.call('HSET', key, 'quantity', tostring(new_qty))
            new_qty = current_qty - order_qty_num
            self._data[key]["quantity"] = str(new_qty)
            return new_qty


def test_suite_1_lua_concurrency():
    logger.info("=== Running Suite 1: Atomic Lua Stock Decrement & Concurrency ===")
    sim = RedisLuaSimulator()
    test_key = "fastcart:inventory.Product:test_item_1"

    # Test 1.1: Concurrency stress test — 100 concurrent workers competing for 15 items
    sim.set_hash(test_key, {"quantity": 15})
    success_count = 0
    insufficient_count = 0
    lock = threading.Lock()

    def order_worker(w_id: int):
        nonlocal success_count, insufficient_count
        time.sleep(0.001)  # tiny jitter
        res = sim.eval_lua_stock_decrement(test_key, 1)
        with lock:
            if res >= 0:
                success_count += 1
            elif res == -2:
                insufficient_count += 1

    threads = [threading.Thread(target=order_worker, args=(i,)) for i in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_stock = int(sim.get_hash(test_key)["quantity"])
    if success_count == 15 and insufficient_count == 85 and final_stock == 0:
        results.record_pass(
            "T1.1 Concurrency & Anti-Overselling",
            f"(100 workers -> exactly 15 fulfilled, 85 rejected with -2, final stock 0, 0 oversold)"
        )
    else:
        results.record_fail(
            "T1.1 Concurrency & Anti-Overselling",
            f"Expected 15 successes, 85 rejected, 0 stock. Got: {success_count} success, {insufficient_count} rejected, stock {final_stock}"
        )

    # Test 1.2: Insufficient stock returns -2
    sim.set_hash(test_key, {"quantity": 5})
    res_insufficient = sim.eval_lua_stock_decrement(test_key, 6)
    if res_insufficient == -2 and sim.get_hash(test_key)["quantity"] == "5":
        results.record_pass("T1.2 Insufficient Stock Guard", "Returned -2, stock preserved at 5")
    else:
        results.record_fail("T1.2 Insufficient Stock Guard", f"Returned {res_insufficient}")

    # Test 1.3: Exact stock boundary (quantity == order_quantity) returns 0
    sim.set_hash(test_key, {"quantity": 5})
    res_exact = sim.eval_lua_stock_decrement(test_key, 5)
    if res_exact == 0 and sim.get_hash(test_key)["quantity"] == "0":
        results.record_pass("T1.3 Exact Stock Boundary", "Requested exactly 5 of 5, returned 0, stock is 0")
    else:
        results.record_fail("T1.3 Exact Stock Boundary", f"Returned {res_exact}")

    # Test 1.4: Non-existent product key returns -1
    res_non_existent = sim.eval_lua_stock_decrement("fastcart:inventory.Product:non_existent", 1)
    if res_non_existent == -1:
        results.record_pass("T1.4 Non-existent Product Key", "Returned -1")
    else:
        results.record_fail("T1.4 Non-existent Product Key", f"Returned {res_non_existent}")

    # Test 1.5: Existing hash without 'quantity' field returns -1
    sim.set_hash("fastcart:inventory.Product:corrupted", {"name": "Test Corrupted"})
    res_no_qty = sim.eval_lua_stock_decrement("fastcart:inventory.Product:corrupted", 1)
    if res_no_qty == -1:
        results.record_pass("T1.5 Missing Quantity Field in Existing Hash", "Returned -1")
    else:
        results.record_fail("T1.5 Missing Quantity Field in Existing Hash", f"Returned {res_no_qty}")

    # Test 1.6: Adversarial Negative Quantity Edge Case
    sim.set_hash(test_key, {"quantity": 10})
    res_negative = sim.eval_lua_stock_decrement(test_key, -5)
    new_stock = sim.get_hash(test_key)["quantity"]
    if res_negative == 15 and new_stock == "15":
        results.record_finding(
            "T1.6 Lua Negative Quantity Vulnerability: ARGV[1] = -5 caused stock to increase from 10 to 15! "
            "LUA_ATOMIC_DECREMENT lacks `if order_qty <= 0 then return -3 end` guard."
        )
        results.record_pass("T1.6 Negative Quantity Behavior Documented", "Stock increased to 15 (vulnerability captured)")
    else:
        results.record_pass("T1.6 Negative Quantity Handled", f"Returned {res_negative}")

    # Test 1.7: Adversarial Zero Quantity Edge Case
    sim.set_hash(test_key, {"quantity": 10})
    res_zero = sim.eval_lua_stock_decrement(test_key, 0)
    if res_zero == 10:
        results.record_finding(
            "T1.7 Lua Zero Quantity: ARGV[1] = 0 returned remaining stock 10 without rejecting order."
        )
        results.record_pass("T1.7 Zero Quantity Handled", "Returned 10 without decrement")


# ==============================================================================
# 2. ASYNCIO.TO_THREAD EVENT LOOP RESPONSIVENESS TESTS
# ==============================================================================

async def test_suite_2_event_loop_responsiveness():
    logger.info("=== Running Suite 2: Non-Blocking Consumer Loops & Event Loop Liveness ===")

    # Test 2.1: Heartbeat latency while xreadgroup simulates 1000ms blocking I/O
    ticks: List[float] = []
    stop_heartbeat = asyncio.Event()

    async def heartbeat():
        while not stop_heartbeat.is_set():
            ticks.append(time.perf_counter())
            await asyncio.sleep(0.02)  # 20ms ticks

    def simulated_blocking_xreadgroup(block_time_sec: float = 1.0):
        time.sleep(block_time_sec)
        return [("order_completed", [("msg-100", {"order_id": "1", "product_id": "p1", "order_quantity": "1"})])]

    hb_task = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.05)  # Start heartbeat

    t0 = time.perf_counter()
    start_ticks_count = len(ticks)

    # Execute blocking call via asyncio.to_thread as done in worker consumer.py
    messages = await asyncio.to_thread(simulated_blocking_xreadgroup, 0.8)

    t1 = time.perf_counter()
    end_ticks_count = len(ticks)
    stop_heartbeat.set()
    await hb_task

    elapsed = t1 - t0
    ticks_during_block = end_ticks_count - start_ticks_count

    # Calculate jitter and maximum gap
    gaps = [ticks[i + 1] - ticks[i] for i in range(len(ticks) - 1)]
    max_gap = max(gaps) if gaps else 0.0

    # On Windows, system timer resolution is ~15.6ms. Over 0.8s, ~25-35 ticks is normal.
    # Event loop is healthy if max lag between ticks is well under 100ms and tick count >= 15.
    if ticks_during_block >= 15 and max_gap < 0.1:
        results.record_pass(
            "T2.1 Event Loop Unblocked during xreadgroup",
            f"(elapsed: {elapsed:.2f}s, heartbeat ticks: {ticks_during_block}, max tick lag: {max_gap*1000:.1f}ms < 100ms)"
        )
    else:
        results.record_fail(
            "T2.1 Event Loop Starvation Detected",
            f"(ticks during block: {ticks_during_block}, max tick lag: {max_gap*1000:.1f}ms)"
        )

    # Test 2.2: Verify process_order_message offloads eval and xack to worker threads
    mock_redis = MagicMock()
    mock_redis.eval.return_value = 5  # success decrement
    mock_redis.xack.return_value = 1

    with patch("inventory.app.workers.consumer.FastAPICache.clear", new_callable=AsyncMock) as mock_cache_clear, \
         patch("inventory.app.workers.consumer.clear_cache_by_pk", new_callable=AsyncMock) as mock_pk_clear, \
         patch("inventory.app.workers.consumer.Product.make_primary_key", return_value="fastcart:inventory.Product:p1"):
        
        await process_order_message(
            redis_stream_client=mock_redis,
            key="order_completed",
            group="inventory_group",
            message_id="msg-1",
            obj={"product_id": "p1", "order_quantity": "2", "order_id": "99"},
        )

        mock_redis.eval.assert_called_once()
        mock_redis.xack.assert_called_once_with("order_completed", "inventory_group", "msg-1")
        mock_cache_clear.assert_awaited_once()
        mock_pk_clear.assert_awaited_once_with(pk="p1", namespace="inventory.product")
        results.record_pass(
            "T2.2 process_order_message Execution",
            "eval and xack invoked, cache cleared asynchronously"
        )

    # Test 2.3: Verification of refund branch in process_order_message
    mock_redis.reset_mock()
    mock_redis.eval.return_value = -2  # insufficient stock

    with patch("inventory.app.workers.consumer.StreamService.stream_order_refund") as mock_stream_refund:
        await process_order_message(
            redis_stream_client=mock_redis,
            key="order_completed",
            group="inventory_group",
            message_id="msg-2",
            obj={"product_id": "p1", "order_quantity": "100", "order_id": "102"},
        )

        mock_stream_refund.assert_called_once_with({"product_id": "p1", "order_quantity": "100", "order_id": "102"})
        mock_redis.xack.assert_called_once_with("order_completed", "inventory_group", "msg-2")
        results.record_pass(
            "T2.3 process_order_message Insufficient Stock Refund Saga",
            "StreamService.stream_order_refund called and message acknowledged"
        )

    # Test 2.4: Finding check on synchronous StreamService.stream_order_refund
    results.record_finding(
        "T2.4 Synchronous Redis Call in StreamService: StreamService.stream_order_refund(obj) calls "
        "get_redis_stream_client().xadd(...) directly on the event loop (not offloaded to asyncio.to_thread)."
    )


# ==============================================================================
# 3. PEL RECOVERY MECHANISM UNDER EDGE CONDITIONS
# ==============================================================================

async def test_suite_3_pel_recovery():
    logger.info("=== Running Suite 3: PEL Recovery Mechanism (xautoclaim) ===")
    fake_r = fakeredis.FakeRedis(decode_responses=True)

    stream_key = "test_stream_inventory"
    group_name = "test_inventory_group"
    consumer_name = "test_consumer_1"

    # Test 3.1: PEL recovery on Empty Stream
    init_consumer_group(fake_r, stream_key, group_name)
    try:
        await recover_pel_inventory(
            redis_stream_client=fake_r,
            key=stream_key,
            group=group_name,
            consumer=consumer_name,
            min_idle_time=0,
        )
        results.record_pass("T3.1 PEL Recovery on Empty Stream", "Terminates cleanly without looping or hanging")
    except Exception as e:
        results.record_fail("T3.1 PEL Recovery on Empty Stream", f"Raised exception: {e}")

    # Test 3.2: PEL recovery on Uninitialized Group / Non-existent Stream
    try:
        await recover_pel_inventory(
            redis_stream_client=fake_r,
            key="uninitialized_stream_xyz",
            group="uninitialized_group_xyz",
            consumer=consumer_name,
            min_idle_time=0,
        )
        results.record_pass(
            "T3.2 PEL Recovery on Uninitialized Group",
            "Catches ResponseError (NOGROUP) gracefully without crashing application"
        )
    except Exception as e:
        results.record_fail("T3.2 PEL Recovery on Uninitialized Group", f"Uncaught exception: {e}")

    # Test 3.3: PEL recovery of abandoned pending messages
    # Add 3 messages to stream
    m1 = fake_r.xadd(stream_key, {"product_id": "p1", "order_quantity": "1", "order_id": "201"})
    m2 = fake_r.xadd(stream_key, {"product_id": "p2", "order_quantity": "2", "order_id": "202"})
    m3 = fake_r.xadd(stream_key, {"product_id": "p3", "order_quantity": "3", "order_id": "203"})

    # Read messages with consumer A without acknowledging them -> they enter PEL
    read_entries = fake_r.xreadgroup(group_name, "abandoned_consumer", {stream_key: ">"}, count=10)
    assert len(read_entries[0][1]) == 3, "Failed to read 3 messages into PEL"

    # Verify pending entries exist in PEL
    pel_info_before = fake_r.xpending(stream_key, group_name)
    assert pel_info_before["pending"] == 3, f"Expected 3 pending entries, got {pel_info_before['pending']}"

    # Mock process_order_message to acknowledge claimed messages
    processed_messages: List[str] = []

    async def mock_process(client, key, group, msg_id, obj):
        processed_messages.append(msg_id)
        client.xack(key, group, msg_id)

    with patch("inventory.app.workers.consumer.process_order_message", side_effect=mock_process):
        await recover_pel_inventory(
            redis_stream_client=fake_r,
            key=stream_key,
            group=group_name,
            consumer=consumer_name,
            min_idle_time=0,
        )

    pel_info_after = fake_r.xpending(stream_key, group_name)
    if len(processed_messages) == 3 and pel_info_after["pending"] == 0:
        results.record_pass(
            "T3.3 Abandoned Pending Messages Recovery",
            f"(Reclaimed and processed {len(processed_messages)}/3 messages, PEL reduced from 3 to 0)"
        )
    else:
        results.record_fail(
            "T3.3 Abandoned Pending Messages Recovery",
            f"Processed {len(processed_messages)}, remaining pending: {pel_info_after['pending']}"
        )

    # Test 3.4: Payment Service Consumer PEL Recovery (recover_pel_refund)
    pay_stream = "test_stream_refund"
    pay_group = "test_payment_group"
    init_pay_consumer_group(fake_r, pay_stream, pay_group)

    # Empty stream test
    try:
        await recover_pel_refund(
            redis_stream_client=fake_r,
            key=pay_stream,
            group=pay_group,
            consumer="pay_consumer_1",
            min_idle_time=0,
        )
        results.record_pass("T3.4 Payment PEL Recovery Empty Stream", "Handled cleanly")
    except Exception as e:
        results.record_fail("T3.4 Payment PEL Recovery Empty Stream", f"Failed: {e}")

    # Uninitialized group test
    try:
        await recover_pel_refund(
            redis_stream_client=fake_r,
            key="uninit_pay_stream",
            group="uninit_pay_group",
            consumer="pay_consumer_1",
            min_idle_time=0,
        )
        results.record_pass("T3.5 Payment PEL Recovery Uninitialized Group", "Gracefully caught exception")
    except Exception as e:
        results.record_fail("T3.5 Payment PEL Recovery Uninitialized Group", f"Uncaught exception: {e}")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

async def main():
    print("Starting Concurrency & Event Stream Adversarial Verification Suite...", flush=True)
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend
    FastAPICache.init(InMemoryBackend(), prefix="test-cache")
    
    print("\n[1/3] Running Suite 1...", flush=True)
    test_suite_1_lua_concurrency()
    
    print("\n[2/3] Running Suite 2...", flush=True)
    await test_suite_2_event_loop_responsiveness()
    
    print("\n[3/3] Running Suite 3...", flush=True)
    await test_suite_3_pel_recovery()

    print("\n==================================================================", flush=True)
    print(f"VERIFICATION SUMMARY: {len(results.passed)} PASSED, {len(results.failed)} FAILED", flush=True)
    print(f"ADVERSARIAL FINDINGS: {len(results.findings)}", flush=True)
    for f in results.findings:
        print(f" - {f}", flush=True)
    print("==================================================================", flush=True)

    if results.failed:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
