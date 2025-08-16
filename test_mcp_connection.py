#!/usr/bin/env python3
"""
Test MCP server connection and functionality.
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_mcp_status():
    """Test MCP server status."""
    print("🔍 Testing MCP server status...")
    
    try:
        response = requests.get(f"{BASE_URL}/mcp/status")
        if response.status_code == 200:
            data = response.json()
            print("✅ MCP server is running!")
            print(f"   - Enabled: {data['mcp_enabled']}")
            print(f"   - Initialized: {data['mcp_initialized']}")
            print(f"   - Server name: {data['server_info']['server_name']}")
            print(f"   - Tools available: {data['server_info']['tools_available']}")
            return True
        else:
            print(f"❌ MCP status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to MCP server: {e}")
        return False

def test_mcp_tools():
    """Test MCP tools functionality."""
    print("\n🛠️  Testing MCP tools...")
    
    # Test 1: Get Astronomy Picture of the Day
    print("\n1. Testing get_astronomy_picture...")
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/tools/get_astronomy_picture",
            params={"date": "2024-01-15"}
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ APOD tool working!")
            print(f"   - Title: {data.get('title', 'N/A')}")
            print(f"   - Date: {data.get('date', 'N/A')}")
            print(f"   - Media type: {data.get('media_type', 'N/A')}")
            print(f"   - Has metadata: {'_metadata' in data}")
        else:
            print(f"❌ APOD tool failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ APOD tool error: {e}")
    
    # Test 2: Search Mars rover photos
    print("\n2. Testing search_mars_rover_photos...")
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/tools/search_mars_rover_photos",
            json={
                "rover": "curiosity",
                "sol": 1000,
                "camera": "MAST"
            }
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ Mars rover photos tool working!")
            print(f"   - Rover: {data.get('rover', 'N/A')}")
            print(f"   - Sol: {data.get('sol', 'N/A')}")
            print(f"   - Total photos: {data.get('total_photos', 'N/A')}")
            print(f"   - Has metadata: {'_metadata' in data}")
        else:
            print(f"❌ Mars rover photos tool failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Mars rover photos tool error: {e}")
    
    # Test 3: Find Near Earth Objects
    print("\n3. Testing find_near_earth_objects...")
    try:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/mcp/tools/find_near_earth_objects",
            json={
                "start_date": start_date,
                "end_date": end_date
            }
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ NEO tool working!")
            print(f"   - Total objects: {data.get('total_objects', 'N/A')}")
            print(f"   - Hazardous count: {data.get('hazardous_count', 'N/A')}")
            print(f"   - Date range: {start_date} to {end_date}")
            print(f"   - Has metadata: {'_metadata' in data}")
        else:
            print(f"❌ NEO tool failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ NEO tool error: {e}")

def test_openapi_docs():
    """Test that MCP endpoints are in OpenAPI docs."""
    print("\n📚 Testing OpenAPI documentation...")
    
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            openapi_data = response.json()
            paths = openapi_data.get("paths", {})
            
            mcp_endpoints = [
                "/mcp/tools/get_astronomy_picture",
                "/mcp/tools/search_mars_rover_photos",
                "/mcp/tools/find_near_earth_objects"
            ]
            
            print("✅ OpenAPI docs accessible!")
            for endpoint in mcp_endpoints:
                if endpoint in paths:
                    print(f"   ✅ {endpoint} documented")
                else:
                    print(f"   ❌ {endpoint} missing from docs")
        else:
            print(f"❌ OpenAPI docs failed: {response.status_code}")
    except Exception as e:
        print(f"❌ OpenAPI docs error: {e}")

def main():
    """Run all MCP tests."""
    print("🚀 Testing MCP Server Connection\n")
    print("Make sure your server is running at http://localhost:8000")
    print("=" * 50)
    
    # Test MCP status
    if not test_mcp_status():
        print("\n❌ MCP server is not accessible. Make sure it's running with MCP enabled.")
        return
    
    # Test MCP tools
    test_mcp_tools()
    
    # Test OpenAPI docs
    test_openapi_docs()
    
    print("\n" + "=" * 50)
    print("🎉 MCP server testing complete!")
    print("\n💡 Next steps:")
    print("   - Visit http://localhost:8000/docs to see the interactive API docs")
    print("   - Check http://localhost:8000/mcp/status for MCP server status")
    print("   - Use an MCP client to connect to the server")

if __name__ == "__main__":
    main()