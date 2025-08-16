#!/usr/bin/env python3
"""
Full MCP protocol compliant bridge for NASA MCP server.
This implements the complete MCP protocol including initialization.
"""

import json
import sys
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, List, Optional

class NASAMCPServer:
    """Full MCP protocol server for NASA data."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.initialized = False
        self.server_info = {
            "name": "nasa-mcp-demo",
            "version": "1.0.0"
        }
    
    def make_request(self, endpoint: str, data: Dict[str, Any] = None, params: Dict[str, str] = None) -> Dict[str, Any]:
        """Make HTTP request using urllib."""
        url = f"{self.base_url}{endpoint}"
        
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        headers = {'Content-Type': 'application/json'}
        
        if data:
            data_bytes = json.dumps(data).encode('utf-8')
        else:
            data_bytes = None
        
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_text = e.read().decode('utf-8') if e.fp else str(e)
            raise Exception(f"HTTP {e.code}: {error_text}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        self.initialized = True
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": self.server_info
        }
    
    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        if not self.initialized:
            raise Exception("Server not initialized")
        
        tools = [
            {
                "name": "get_astronomy_picture",
                "description": "Get NASA's Astronomy Picture of the Day (APOD) with detailed information and metadata",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format. If not provided, returns today's APOD",
                            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                        }
                    }
                }
            },
            {
                "name": "search_mars_rover_photos",
                "description": "Search for photos taken by Mars exploration rovers with detailed metadata and analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "rover": {
                            "type": "string",
                            "description": "Name of the Mars rover (curiosity, perseverance, opportunity, spirit)"
                        },
                        "sol": {
                            "type": "integer",
                            "description": "Martian sol (day) number since rover landing",
                            "minimum": 0
                        },
                        "camera": {
                            "type": "string",
                            "description": "Optional camera name filter (FHAZ, RHAZ, MAST, NAVCAM, etc.)"
                        }
                    },
                    "required": ["rover", "sol"]
                }
            },
            {
                "name": "find_near_earth_objects",
                "description": "Find Near Earth Objects (asteroids and comets) with comprehensive analysis and risk assessment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format",
                            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format",
                            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                        }
                    },
                    "required": ["start_date", "end_date"]
                }
            }
        ]
        
        return {"tools": tools}
    
    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        if not self.initialized:
            raise Exception("Server not initialized")
        
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Map tool names to endpoints
        endpoint_map = {
            "get_astronomy_picture": "/mcp/tools/get_astronomy_picture",
            "search_mars_rover_photos": "/mcp/tools/search_mars_rover_photos",
            "find_near_earth_objects": "/mcp/tools/find_near_earth_objects"
        }
        
        if name not in endpoint_map:
            raise Exception(f"Unknown tool: {name}")
        
        endpoint = endpoint_map[name]
        
        try:
            if name == "get_astronomy_picture":
                # Use query parameters for APOD
                params_dict = {}
                if "date" in arguments:
                    params_dict["date"] = arguments["date"]
                result = self.make_request(endpoint, params=params_dict)
            else:
                # Use JSON body for other tools
                result = self.make_request(endpoint, data=arguments)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error calling {name}: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = self.handle_tools_call(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

def main():
    """Main MCP server loop."""
    server = NASAMCPServer()
    
    # Send server info on startup
    server_info = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            request = json.loads(line)
            response = server.handle_request(request)
            
            print(json.dumps(response))
            sys.stdout.flush()
        
        except json.JSONDecodeError:
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()