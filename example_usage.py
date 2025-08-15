#!/usr/bin/env python3
"""
Example usage of the NASA MCP Demo API.

This script demonstrates how to use the FastAPI endpoints to retrieve NASA data.
"""

import asyncio
import httpx
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"


async def test_api_endpoints():
    """Test all API endpoints with example requests."""

    async with httpx.AsyncClient() as client:
        print("🚀 Testing NASA MCP Demo API")
        print("=" * 50)

        # Test root endpoint
        print("\n1. Testing root endpoint...")
        response = await client.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Name: {data['name']}")
            print(f"✅ Version: {data['version']}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")

        # Test health check
        print("\n2. Testing health check...")
        response = await client.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Overall Status: {data['status']}")
            print(f"✅ NASA API: {data['nasa_api']}")
            print(f"✅ Cache: {data['cache']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")

        # Test APOD endpoint
        print("\n3. Testing APOD endpoint...")
        response = await client.get(f"{BASE_URL}/apod")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ APOD Date: {data['date']}")
            print(f"✅ Title: {data['title'][:50]}...")
            print(f"✅ Media Type: {data['media_type']}")
            print(f"✅ Is Recent: {data['is_recent']}")
        else:
            print(f"❌ APOD endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")

        # Test APOD with specific date
        print("\n4. Testing APOD with specific date...")
        test_date = "2024-01-01"
        response = await client.get(f"{BASE_URL}/apod?date={test_date}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ APOD for {test_date}: {data['title'][:50]}...")
        else:
            print(f"❌ APOD with date failed: {response.status_code}")

        # Test Mars photos endpoint
        print("\n5. Testing Mars photos endpoint...")
        response = await client.get(f"{BASE_URL}/mars-photos/curiosity?sol=1000")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Rover: {data['rover']}")
            print(f"✅ Sol: {data['sol']}")
            print(f"✅ Total Photos: {data['total_photos']}")
            print(f"✅ Cameras Used: {', '.join(data['cameras_used'])}")
        else:
            print(f"❌ Mars photos failed: {response.status_code}")
            print(f"   Error: {response.text}")

        # Test NEO endpoint
        print("\n6. Testing NEO endpoint...")
        start_date = "2024-01-01"
        end_date = "2024-01-07"
        response = await client.get(
            f"{BASE_URL}/neo?start_date={start_date}&end_date={end_date}"
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Total Objects: {data['total_objects']}")
            print(f"✅ Hazardous Count: {data['hazardous_count']}")
            print(
                f"✅ Date Range: {data['date_range']['start_date']} to {data['date_range']['end_date']}"
            )
            if data["closest_approach"]:
                print(f"✅ Closest Object: {data['closest_approach']['name']}")
        else:
            print(f"❌ NEO endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")

        # Test rovers info endpoint
        print("\n7. Testing rovers info endpoint...")
        response = await client.get(f"{BASE_URL}/rovers")
        if response.status_code == 200:
            data = response.json()
            active_rovers = [
                name
                for name, info in data["rovers"].items()
                if info["status"] == "active"
            ]
            print(f"✅ Active Rovers: {', '.join(active_rovers)}")
            print(f"✅ Total Rovers: {len(data['rovers'])}")
        else:
            print(f"❌ Rovers info failed: {response.status_code}")

        # Test API documentation
        print("\n8. Testing API documentation...")
        response = await client.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            data = response.json()
            print(
                f"✅ OpenAPI Schema: {data['info']['title']} v{data['info']['version']}"
            )
            print(f"✅ Available Paths: {len(data['paths'])}")
        else:
            print(f"❌ OpenAPI schema failed: {response.status_code}")

        print("\n" + "=" * 50)
        print("🎉 API testing complete!")
        print("\n📖 View full API documentation at: http://localhost:8000/docs")
        print("📖 View ReDoc documentation at: http://localhost:8000/redoc")


if __name__ == "__main__":
    print("Starting NASA MCP Demo API tests...")
    print("Make sure the server is running with: python run_server.py")
    print()

    try:
        asyncio.run(test_api_endpoints())
    except httpx.ConnectError:
        print("❌ Could not connect to the API server.")
        print("   Please start the server first with: python run_server.py")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
