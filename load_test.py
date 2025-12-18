#!/usr/bin/env python3
"""
Comprehensive load testing script for HTTP servers
"""
import asyncio
import aiohttp
import time
import statistics
import argparse
from typing import List, Tuple, Optional


class RequestResult:
    def __init__(self, request_num: int, status: Optional[int], 
                 error: Optional[str], duration: float):
        self.request_num = request_num
        self.status = status
        self.error = error
        self.duration = duration


async def send_request(session: aiohttp.ClientSession, url: str, 
                       request_num: int) -> RequestResult:
    """Send a single HTTP request and measure its duration"""
    start = time.time()
    try:
        async with session.get(url) as response:
            status = response.status
            # Read response body to ensure full request completion
            await response.read()
            duration = time.time() - start
            return RequestResult(request_num, status, None, duration)
    except Exception as e:
        duration = time.time() - start
        return RequestResult(request_num, None, str(e), duration)


async def burst_test(url: str, total_requests: int, concurrency: int) -> Tuple[List[RequestResult], float]:
    """Send all requests as fast as possible with limited concurrency"""
    print(f"\n{'='*70}")
    print(f"BURST TEST: {total_requests} requests, max {concurrency} concurrent")
    print(f"{'='*70}")
    
    start_time = time.time()
    results = []
    
    # Use a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)
    
    async def bounded_request(session: aiohttp.ClientSession, req_num: int):
        async with semaphore:
            return await send_request(session, url, req_num)
    
    connector = aiohttp.TCPConnector(limit=concurrency)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [bounded_request(session, i + 1) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    return results, elapsed


async def sustained_test(url: str, total_requests: int, duration_seconds: int) -> Tuple[List[RequestResult], float]:
    """Spread requests evenly over a time period"""
    print(f"\n{'='*70}")
    print(f"SUSTAINED TEST: {total_requests} requests over {duration_seconds} seconds")
    print(f"{'='*70}")
    
    delay_between_requests = duration_seconds / total_requests
    start_time = time.time()
    
    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        
        for i in range(total_requests):
            if i > 0:
                await asyncio.sleep(delay_between_requests)
            
            task = asyncio.create_task(send_request(session, url, i + 1))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    return results, elapsed


def print_results(results: List[RequestResult], elapsed: float, test_name: str):
    """Print detailed analysis of test results"""
    total_requests = len(results)
    successful = sum(1 for r in results if r.status and not r.error)
    failed = total_requests - successful
    
    # Status code distribution
    status_codes = {}
    for r in results:
        if r.status:
            status_codes[r.status] = status_codes.get(r.status, 0) + 1
    
    # Response time statistics (for successful requests)
    successful_durations = [r.duration for r in results if r.status and not r.error]
    
    print(f"\n{test_name} Results:")
    print(f"{'-'*70}")
    print(f"Total time: {elapsed:.2f} seconds")
    print(f"Total requests: {total_requests}")
    print(f"Successful: {successful} ({successful/total_requests*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total_requests*100:.1f}%)")
    print(f"Requests per second: {total_requests/elapsed:.2f}")
    
    if successful_durations:
        print(f"\nResponse Time Statistics:")
        print(f"  Min: {min(successful_durations)*1000:.2f}ms")
        print(f"  Max: {max(successful_durations)*1000:.2f}ms")
        print(f"  Mean: {statistics.mean(successful_durations)*1000:.2f}ms")
        print(f"  Median: {statistics.median(successful_durations)*1000:.2f}ms")
        if len(successful_durations) > 1:
            print(f"  Std Dev: {statistics.stdev(successful_durations)*1000:.2f}ms")
        
        # Percentiles
        sorted_durations = sorted(successful_durations)
        p50 = sorted_durations[int(len(sorted_durations) * 0.50)]
        p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
        p99 = sorted_durations[int(len(sorted_durations) * 0.99)]
        print(f"  P50: {p50*1000:.2f}ms")
        print(f"  P95: {p95*1000:.2f}ms")
        print(f"  P99: {p99*1000:.2f}ms")
    
    print(f"\nStatus code distribution:")
    for status, count in sorted(status_codes.items()):
        print(f"  {status}: {count}")
    
    # Show errors if any
    errors = [r for r in results if r.error]
    if errors:
        print(f"\nErrors ({len(errors)}):")
        error_types = {}
        for r in errors:
            error_types[r.error] = error_types.get(r.error, 0) + 1
        for error, count in list(error_types.items())[:5]:
            print(f"  {error}: {count} occurrences")


async def main():
    parser = argparse.ArgumentParser(description='HTTP Server Load Testing Tool')
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Target URL (default: http://localhost:8080)')
    parser.add_argument('--requests', type=int, default=1000,
                       help='Total number of requests (default: 1000)')
    parser.add_argument('--concurrency', type=int, nargs='+', 
                       default=[10, 50, 100, 500],
                       help='Concurrency levels to test (default: 10 50 100 500)')
    parser.add_argument('--sustained-duration', type=int, default=5,
                       help='Duration for sustained test in seconds (default: 5)')
    parser.add_argument('--skip-burst', action='store_true',
                       help='Skip burst tests')
    parser.add_argument('--skip-sustained', action='store_true',
                       help='Skip sustained test')
    
    args = parser.parse_args()
    
    print(f"{'='*70}")
    print(f"HTTP Server Load Testing")
    print(f"{'='*70}")
    print(f"Target: {args.url}")
    print(f"Total requests per test: {args.requests}")
    
    # Run sustained load test
    if not args.skip_sustained:
        results, elapsed = await sustained_test(
            args.url, args.requests, args.sustained_duration
        )
        print_results(results, elapsed, "SUSTAINED LOAD")
    
    # Run burst tests with different concurrency levels
    if not args.skip_burst:
        for concurrency in sorted(args.concurrency):
            results, elapsed = await burst_test(
                args.url, args.requests, concurrency
            )
            print_results(results, elapsed, f"BURST (concurrency={concurrency})")
            
            # Small delay between tests
            await asyncio.sleep(1)
    
    print(f"\n{'='*70}")
    print(f"All tests complete!")
    print(f"{'='*70}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
