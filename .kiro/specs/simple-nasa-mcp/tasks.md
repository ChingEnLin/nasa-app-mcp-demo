# Implementation Plan

- [x] 1. Clean up existing project structure
  - Remove unnecessary directories (demos, extensive tests, documentation files)
  - Keep only essential files needed for the simple implementation
  - Create clean project root with minimal structure
  - _Requirements: 1.1_

- [x] 2. Create simple main.py with FastAPI and NASA endpoints
  - Write single main.py file with FastAPI application
  - Add three NASA API endpoints: /apod, /mars-photos, /neo
  - Include basic httpx client for NASA API calls
  - Add simple error handling for API failures
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 3.2_

- [ ] 3. Add MCP integration to existing FastAPI app
  - Install and configure fastapi_mcp library
  - Create three MCP tools matching the REST endpoints
  - Ensure both REST and MCP work simultaneously
  - Test that existing endpoints continue working
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 4. Create minimal configuration and documentation
  - Add requirements.txt with essential dependencies
  - Create .env.example for NASA API key configuration
  - Write simple README with setup and usage instructions
  - Add basic test file to verify functionality
  - _Requirements: 1.5, 3.3_