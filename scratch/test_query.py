import sys
import os

# Append current directory to path
sys.path.append(os.getcwd())

from agent.sql_agent import build_sql_agent, ask

print("Building agent...")
agent, provider, db = build_sql_agent("claude")
print(f"Provider: {provider}")

question = "What were total sales last month?"
print(f"Asking: {question}")
try:
    res = ask(agent, question)
    print("--- SUCCESS ---")
    print(f"SQL: {res['sql']}")
    print(f"Answer:\n{res['answer']}")
except Exception as e:
    print("--- FAILED ---")
    import traceback
    traceback.print_exc()
