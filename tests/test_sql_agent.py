# tests/test_sql_agent.py
import os
from unittest.mock import MagicMock
from agent.sql_agent import get_available_providers, extract_sql_from_steps, get_llm

def test_get_available_providers(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "mock_gemini_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "mock_anthropic_key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    providers = get_available_providers()
    assert "gemini" in providers
    assert "claude" in providers
    assert "openai" not in providers

def test_extract_sql_from_steps_string():
    # Mocking action structure from Langchain
    action = MagicMock()
    action.tool = "sql_db_query"
    action.tool_input = "SELECT * FROM orders LIMIT 10;"
    
    steps = [(action, "result")]
    sql = extract_sql_from_steps(steps)
    assert sql == "SELECT * FROM orders LIMIT 10;"

def test_extract_sql_from_steps_dict():
    action = MagicMock()
    action.tool = "sql_db_query"
    action.tool_input = {"query": "SELECT * FROM products LIMIT 5;"}
    
    steps = [(action, "result")]
    sql = extract_sql_from_steps(steps)
    assert sql == "SELECT * FROM products LIMIT 5;"

def test_extract_sql_from_steps_none():
    action = MagicMock()
    action.tool = "some_other_tool"
    action.tool_input = "SELECT * FROM customers;"
    
    steps = [(action, "result")]
    sql = extract_sql_from_steps(steps)
    assert sql is None
