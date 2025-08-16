#!/usr/bin/env python3
"""
Test MCP Prompts - Example prompts to test the NASA MCP server
This script shows example prompts you can use with AI clients that support MCP
"""

# Example prompts to test the NASA MCP server
TEST_PROMPTS = [
    # APOD Tests
    "Get today's astronomy picture from NASA",
    "Show me NASA's astronomy picture for January 1, 2024",
    "What was NASA's astronomy picture on December 25, 2023?",
    
    # Mars Rover Tests
    "Show me Mars rover photos from Curiosity on sol 1000",
    "Get photos from the Perseverance rover on sol 500 using the MAST camera",
    "Show me hazard avoidance camera photos from Curiosity on sol 1500",
    "Get recent photos from the Opportunity rover on sol 2000",
    
    # Near Earth Objects Tests
    "Find near earth objects for January 1-7, 2024",
    "Show me asteroids and comets that passed by Earth in December 2023",
    "Find potentially hazardous asteroids from March 1-15, 2024",
    "What near earth objects approached Earth between February 1-7, 2024?",
    
    # Combined Tests
    "Show me today's astronomy picture and find any near earth objects for this week",
    "Get Mars rover photos from Curiosity on sol 1000 and tell me about today's astronomy picture",
    "Find near earth objects for this week and show me recent Mars rover photos",
    
    # Advanced Tests
    "Show me high-resolution images from the Curiosity rover's mast camera on sol 1000, and also get today's astronomy picture",
    "I'm writing a blog post about Mars exploration. Get me some photos from Perseverance rover on sol 800",
    "Help me understand what cameras are available on Mars rovers by showing me photos from different cameras",
    
    # Specific Date Tests
    "Get NASA's astronomy picture for my birthday: 1990-05-15",
    "Show me what near earth objects were detected on New Year's Day 2024",
    "Get Mars rover photos from the day Curiosity landed on Mars (use sol 0)",
]

def print_test_prompts():
    """Print all test prompts with categories"""
    print("🚀 NASA MCP Server Test Prompts")
    print("=" * 50)
    print()
    print("Copy and paste these prompts into your AI client to test the NASA MCP server:")
    print()
    
    categories = [
        ("📸 Astronomy Picture of the Day (APOD)", TEST_PROMPTS[0:3]),
        ("🚀 Mars Rover Photos", TEST_PROMPTS[3:7]),
        ("🌌 Near Earth Objects", TEST_PROMPTS[7:11]),
        ("🔄 Combined Requests", TEST_PROMPTS[11:14]),
        ("⚡ Advanced Requests", TEST_PROMPTS[14:17]),
        ("📅 Specific Date Requests", TEST_PROMPTS[17:20]),
    ]
    
    for category, prompts in categories:
        print(f"{category}")
        print("-" * 30)
        for i, prompt in enumerate(prompts, 1):
            print(f"{i}. {prompt}")
        print()

def print_mcp_tools_info():
    """Print information about available MCP tools"""
    print("🛠️  Available MCP Tools")
    print("=" * 50)
    print()
    
    tools = [
        {
            "name": "get_astronomy_picture",
            "description": "Get NASA's Astronomy Picture of the Day",
            "parameters": [
                "date (optional): Date in YYYY-MM-DD format"
            ],
            "examples": [
                "Get today's astronomy picture",
                "Show me the astronomy picture for 2024-01-01"
            ]
        },
        {
            "name": "search_mars_rover_photos",
            "description": "Search for Mars rover photos",
            "parameters": [
                "rover (required): curiosity, perseverance, opportunity, spirit",
                "sol (required): Martian day number",
                "camera (optional): FHAZ, RHAZ, MAST, NAVCAM, etc."
            ],
            "examples": [
                "Get Curiosity photos from sol 1000",
                "Show Perseverance MAST camera photos from sol 500"
            ]
        },
        {
            "name": "find_near_earth_objects",
            "description": "Find Near Earth Objects for a date range",
            "parameters": [
                "start_date (required): Start date in YYYY-MM-DD format",
                "end_date (required): End date in YYYY-MM-DD format"
            ],
            "examples": [
                "Find NEOs for January 1-7, 2024",
                "Show asteroids from this week"
            ]
        }
    ]
    
    for tool in tools:
        print(f"🔧 {tool['name']}")
        print(f"   {tool['description']}")
        print("   Parameters:")
        for param in tool['parameters']:
            print(f"   • {param}")
        print("   Example prompts:")
        for example in tool['examples']:
            print(f"   • \"{example}\"")
        print()

def print_configuration_info():
    """Print MCP configuration information"""
    print("⚙️  MCP Configuration")
    print("=" * 50)
    print()
    print("The NASA MCP server is configured in:")
    print("• Kiro: .kiro/settings/mcp.json")
    print("• VS Code: .vscode/mcp.json")
    print()
    print("Server command:")
    print("python /path/to/your/project/mcp_bridge.py")
    print()
    print("Make sure to use your virtual environment's Python:")
    print("/path/to/your/project/venv/bin/python")
    print()

if __name__ == "__main__":
    print_test_prompts()
    print_mcp_tools_info()
    print_configuration_info()
    
    print("💡 Tips:")
    print("• Make sure your .env file has NASA_API_KEY set (or use DEMO_KEY)")
    print("• The MCP server uses the same NASA APIs as the FastAPI server")
    print("• Rate limit: 1000 requests per hour")
    print("• All tools are auto-approved in the Kiro configuration")
    print()
    print("🔗 For more information, see MCP_USAGE.md")