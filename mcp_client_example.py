#!/usr/bin/env python3
"""
Example MCP client to connect to the NASA MCP server.
"""

import asyncio
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_client():
    """Test connecting to MCP server as a client."""
    print("🔌 Testing MCP client connection...")

    # For HTTP-based MCP server, we'll use direct HTTP calls
    # since the fastapi_mcp creates HTTP endpoints

    async with httpx.AsyncClient() as client:
        # Test MCP tools via HTTP
        print("\n🛠️  Testing MCP tools via HTTP client...")

        # Test Mars rover photos
        print("1. Testing Mars rover photos...")
        try:
            response = await client.post(
                "http://localhost:8000/mcp/tools/search_mars_rover_photos",
                json={"rover": "perseverance", "sol": 100},
            )
            if response.status_code == 200:
                data = response.json()
                print(
                    f"✅ Found {data['total_photos']} photos from Perseverance sol 100"
                )
                print(f"   Cameras used: {', '.join(data['cameras_used'])}")
                if data["_metadata"]:
                    print(
                        f"   Mission context: {data['_metadata']['rover_info']['mission_context']}"
                    )
            else:
                print(f"❌ Request failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test NEO data
        print("\n2. Testing Near Earth Objects...")
        try:
            response = await client.post(
                "http://localhost:8000/mcp/tools/find_near_earth_objects",
                json={"start_date": "2025-08-10", "end_date": "2025-08-16"},
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Found {data['total_objects']} Near Earth Objects")
                print(f"   Hazardous objects: {data['hazardous_count']}")
                print(f"   Size categories: {data['size_categories']}")
                if data["closest_approach"]:
                    print(
                        f"   Closest approach: {data['closest_approach']['name']} at {data['closest_approach']['miss_distance_km']:,.0f} km"
                    )
            else:
                print(f"❌ Request failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Run MCP client test."""
    print("🚀 NASA MCP Client Test")
    print("=" * 40)

    asyncio.run(test_mcp_client())

    print("\n" + "=" * 40)
    print("✨ MCP client testing complete!")
    print("\n💡 Your MCP server is ready for:")
    print("   - AI model integration")
    print("   - MCP client applications")
    print("   - Custom tool development")


if __name__ == "__main__":
    main()
