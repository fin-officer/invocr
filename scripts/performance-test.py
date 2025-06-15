#!/usr/bin/env python3
"""
Performance testing script for InvOCR
Tests various operations and measures performance
"""

import asyncio
import time
import statistics
from pathlib import Path
from typing import List, Dict
import tempfile
import json

import httpx
from PIL import Image
import numpy as np


class PerformanceTest:
    """Performance testing suite for InvOCR"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []

    async def test_api_health(self) -> Dict:
        """Test API health endpoint performance"""
        print("🔍 Testing API health endpoint...")

        times = []
        async with httpx.AsyncClient() as client:
            for _ in range(10):
                start = time.time()
                response = await client.get(f"{self.base_url}/health")
                end = time.time()

                if response.status_code == 200:
                    times.append(end - start)

        return {
            "test": "api_health",
            "avg_time": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "requests": len(times)
        }

    async def test_image_conversion(self) -> Dict:
        """Test image to JSON conversion performance"""
        print("🖼️  Testing image conversion...")

        # Create test image
        img_array = np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            img.save(tmp.name)

            times = []
            async with httpx.AsyncClient(timeout=60.0) as client:
                for _ in range(3):  # Fewer iterations for OCR
                    start = time.time()

                    with open(tmp.name, 'rb') as f:
                        files = {"file": f}
                        data = {"languages": "en", "document_type": "invoice"}
                        response = await client.post(
                            f"{self.base_url}/convert/img2json",
                            files=files,
                            data=data
                        )

                    end = time.time()

                    if response.status_code == 200:
                        times.append(end - start)

            Path(tmp.name).unlink()

        return {
            "test": "image_conversion",
            "avg_time": statistics.mean(times) if times else 0,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "requests": len(times)
        }

    async def test_json_to_xml(self) -> Dict:
        """Test JSON to XML conversion performance"""
        print("📄 Testing JSON to XML conversion...")

        test_data = {
            "document_number": "PERF/TEST/001",
            "document_date": "2025-06-15",
            "seller": {"name": "Test Company", "tax_id": "123456789"},
            "buyer": {"name": "Test Client", "tax_id": "987654321"},
            "items": [
                {"description": f"Item {i}", "quantity": 1, "unit_price": 100, "total_price": 100}
                for i in range(10)
            ],
            "totals": {"subtotal": 1000, "tax_amount": 230, "total": 1230, "tax_rate": 23}
        }

        times = []
        async with httpx.AsyncClient() as client:
            for _ in range(20):
                start = time.time()
                response = await client.post(
                    f"{self.base_url}/convert/json2xml",
                    json=test_data
                )
                end = time.time()

                if response.status_code == 200:
                    times.append(end - start)

        return {
            "test": "json_to_xml",
            "avg_time": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "requests": len(times)
        }

    async def test_concurrent_requests(self) -> Dict:
        """Test concurrent request handling"""
        print("🚀 Testing concurrent requests...")

        async def make_request(client):
            start = time.time()
            response = await client.get(f"{self.base_url}/info")
            end = time.time()
            return end - start if response.status_code == 200 else None

        async with httpx.AsyncClient() as client:
            # Test with 10 concurrent requests
            tasks = [make_request(client) for _ in range(10)]
            results = await asyncio.gather(*tasks)

            valid_times = [t for t in results if t is not None]

        return {
            "test": "concurrent_requests",
            "avg_time": statistics.mean(valid_times) if valid_times else 0,
            "min_time": min(valid_times) if valid_times else 0,
            "max_time": max(valid_times) if valid_times else 0,
            "requests": len(valid_times),
            "concurrent": 10
        }

    async def run_all_tests(self):
        """Run all performance tests"""
        print("🎯 Starting InvOCR Performance Tests")
        print("=" * 50)

        tests = [
            self.test_api_health,
            self.test_json_to_xml,
            self.test_concurrent_requests,
            self.test_image_conversion,  # Run OCR test last (slowest)
        ]

        for test in tests:
            try:
                result = await test()
                self.results.append(result)

                print(f"✅ {result['test']}: {result['avg_time']:.3f}s avg")

            except Exception as e:
                print(f"❌ {test.__name__} failed: {e}")
                self.results.append({
                    "test": test.__name__,
                    "error": str(e)
                })

        return self.results

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 Performance Test Summary")
        print("=" * 50)

        for result in self.results:
            if "error" in result:
                print(f"❌ {result['test']}: ERROR - {result['error']}")
            else:
                print(f"✅ {result['test']}:")
                print(f"   Average: {result['avg_time']:.3f}s")
                print(f"   Min/Max: {result['min_time']:.3f}s / {result['max_time']:.3f}s")
                print(f"   Requests: {result['requests']}")

                # Performance rating
                avg_time = result['avg_time']
                if avg_time < 0.1:
                    rating = "🟢 Excellent"
                elif avg_time < 0.5:
                    rating = "🟡 Good"
                elif avg_time < 2.0:
                    rating = "🟠 Fair"
                else:
                    rating = "🔴 Slow"

                print(f"   Rating: {rating}")
                print()


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="InvOCR Performance Tests")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--output", help="Output file for results")

    args = parser.parse_args()

    # Check if API is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{args.url}/health")
            if response.status_code != 200:
                print("❌ API is not responding properly")
                return
    except Exception as e:
        print(f"❌ Cannot connect to API at {args.url}: {e}")
        print("💡 Make sure the API server is running: poetry run invocr serve")
        return

    # Run tests
    tester = PerformanceTest(args.url)
    results = await tester.run_all_tests()
    tester.print_summary()

    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📁 Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())


