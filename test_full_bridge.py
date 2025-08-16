#!/usr/bin/env python3
"""
Test the full MCP bridge with proper protocol.
"""

import json
import subprocess
import sys

def test_full_bridge():
    """Test the full MCP bridge functionality."""
    print("🔌 Testing full MCP bridge...")
    
    # Start the bridge process
    process = subprocess.Popen(
        ["python3", "mcp_bridge_full.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Test 1: Initialize
        print("\n1. Testing initialize...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            if "result" in response:
                print("✅ Initialize successful")
                print(f"   Protocol version: {response['result'].get('protocolVersion')}")
                print(f"   Server: {response['result'].get('serverInfo', {}).get('name')}")
            else:
                print(f"❌ Initialize failed: {response}")
                return False
        else:
            print("❌ No response to initialize")
            return False
        
        # Test 2: List tools
        print("\n2. Testing tools/list...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            if "result" in response and "tools" in response["result"]:
                tools = response["result"]["tools"]
                print(f"✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']}")
                return True
            else:
                print(f"❌ Tools list failed: {response}")
                return False
        else:
            print("❌ No response to tools/list")
            return False
    
    finally:
        process.terminate()
        process.wait()

def main():
    """Run full bridge test."""
    print("🚀 Testing Full NASA MCP Bridge")
    print("=" * 50)
    print("Make sure your NASA MCP server is running at http://localhost:8000")
    print()
    
    success = test_full_bridge()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Full bridge test passed!")
        print("\n💡 The full bridge should work with Kiro now!")
        print("   - Restart Kiro or reconnect MCP servers")
        print("   - Check the MCP Server view for 'nasa-mcp-demo'")
    else:
        print("❌ Full bridge test failed!")
        print("   - Make sure your NASA server is running")
        print("   - Check the server logs for errors")

if __name__ == "__main__":
    main()