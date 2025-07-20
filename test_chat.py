#!/usr/bin/env python3
"""Test the chat endpoint."""

import requests
import json

# Test the chat endpoint
url = "http://localhost:8000/api/v1/agent/chat"
data = {
    "message": "Hello! I am testing the memory agent system. What is your purpose?",
    "session_id": "test-session-001",
    "stream": False
}

try:
    response = requests.post(url, json=data)
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")