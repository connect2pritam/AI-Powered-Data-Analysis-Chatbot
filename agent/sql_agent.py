# agent/sql_agent.py
import os
import re


from dotenv import load_dotenv
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.agents.agent_types import AgentType
from db.connection import get_langchain_db
from agent.prompts import SQL_AGENT_SYSTEM_PROMPT
from agent.guardrails import is_select_only, enforce_row_limit

# Load environment variables
load_dotenv()

def get_available_providers():
    """Identifies which LLM providers have API keys set in the environment."""
    providers = []
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append("claude")
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        providers.append("gemini")
    if os.getenv("OPENAI_API_KEY"):
        providers.append("openai")
    return providers

def get_llm(provider=None, temperature=0):
    """Initializes the LLM based on the selected provider or available keys."""
    available = get_available_providers()
    if not available:
        return None, None
        
    if not provider:
        provider = os.getenv("DEFAULT_PROVIDER", "")
        if not provider or provider not in available:
            provider = available[0]
            
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash", 
            google_api_key=key, 
            temperature=temperature
        ), "gemini"
    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        model_name = "claude-sonnet-4-6" if base_url else "claude-3-5-sonnet-20241022"
        kwargs = {
            "model_name": model_name,
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "temperature": temperature
        }
        if base_url:
            kwargs["anthropic_api_url"] = base_url
        return ChatAnthropic(**kwargs), "claude"
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o", 
            api_key=os.getenv("OPENAI_API_KEY"), 
            temperature=temperature
        ), "openai"
    else:
        # Fallback to the first available provider
        fallback = available[0]
        return get_llm(fallback, temperature)

def build_sql_agent(provider=None):
    """Creates the LangChain SQL database agent wrapper."""
    db = get_langchain_db()
    llm, selected_provider = get_llm(provider=provider, temperature=0)
    
    if not llm:
        return None, None, db
        
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    
    # For Claude (especially on Vertex AI or local mock gateways that restrict prefill), 
    # use zero-shot-react-description instead of tool-calling.
    use_react = (selected_provider == "claude")
    
    try:
        if use_react:
            agent = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                prefix=SQL_AGENT_SYSTEM_PROMPT,
                verbose=False,
                max_iterations=10,
            )
        else:
            # Use tool-calling for modern agents supporting native function calls
            agent = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                agent_type="tool-calling",
                prefix=SQL_AGENT_SYSTEM_PROMPT,
                verbose=False,
                max_iterations=10,
            )
    except Exception:
        # Fallback to standard Zero Shot React agent type if tool-calling fails
        agent = create_sql_agent(
            llm=llm,
            toolkit=toolkit,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            prefix=SQL_AGENT_SYSTEM_PROMPT,
            verbose=False,
            max_iterations=10,
        )
        
    return agent, selected_provider, db

def parse_fallback_from_error(error_msg: str):
    """Attempts to scrape the SQL query and final answer from a raw LLM output or error string."""
    # Find any SELECT or WITH statement
    sql_match = re.search(r"(SELECT\s+.*)", error_msg, re.IGNORECASE | re.DOTALL)
    sql_query = None
    if sql_match:
        candidate = sql_match.group(1)
        # Truncate at common langchain text patterns or backticks
        candidate = re.split(r"(Observation:|Thought:|Action:|Action Input:|```)", candidate, flags=re.IGNORECASE)[0]
        sql_query = candidate.strip()
        
    if sql_query:
        # Strip trailing semicolon for clean formatting
        if sql_query.endswith(";"):
            sql_query = sql_query[:-1].strip()
        sql_query = re.sub(r"\x1b\[\d+(;\d+)*m", "", sql_query).strip()
        
    # Find Final Answer:
    answer_match = re.search(r"Final Answer:\s*(.*)", error_msg, re.IGNORECASE)
    answer = None
    if answer_match:
        answer = answer_match.group(1)
        answer = re.split(r"(Thought:|Action:|```)", answer, flags=re.IGNORECASE)[0].strip()
        
    # Extract from backticks: "Could not parse LLM output: `...`"
    backtick_match = re.search(r"Could not parse LLM output:\s*`([\s\S]*?)`", error_msg)
    if backtick_match:
        raw_output = backtick_match.group(1).strip()
        
        # If the output contains "I now know the final answer"
        if "I now know the final answer" in raw_output:
            parts = re.split(r"I now know the final answer\.", raw_output, flags=re.IGNORECASE)
            candidate_answer = parts[-1].strip()
            if candidate_answer:
                answer = candidate_answer
        
        if not answer:
            fa_match = re.search(r"Final Answer:\s*(.*)", raw_output, re.IGNORECASE)
            if fa_match:
                answer = fa_match.group(1).strip()
            else:
                lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
                text_lines = [line for line in lines if not any(kw in line.upper() for kw in ["SELECT ", "FROM ", "JOIN ", "WHERE ", "GROUP BY ", "ORDER BY "])]
                if text_lines:
                    answer = "\n".join(text_lines)
                else:
                    answer = raw_output
                    
    if not answer:
        answer = "Analyzed database query."
        
    # Remove thoughts prefix if it bled into the answer
    answer = re.sub(r"Thought:\s*", "", answer, flags=re.IGNORECASE)
    # Remove ANSI escape codes
    answer = re.sub(r"\x1b\[\d+(;\d+)*m", "", answer).strip()
    return answer, sql_query

def ask(agent, question: str) -> dict:
    """Runs the agent, extracts intermediate SQL execution logs, and performs guardrail checks."""
    if not agent:
        return {
            "answer": "Error: SQL Agent is not configured. Please set your API keys in the .env file.",
            "sql": None
        }
        
    try:
        # Execute the agent and retain intermediate chain details
        result = agent.invoke({"input": question}, return_intermediate_steps=True)
        sql_used = extract_sql_from_steps(result.get("intermediate_steps", []))
        answer = result["output"]
    except Exception as e:
        error_str = str(e)
        # Check if this is an output parsing failure or contains LLM outputs
        if any(kw in error_str.lower() for kw in ["parsing", "output", "final answer", "select", "know the final answer"]):
            answer, sql_used = parse_fallback_from_error(error_str)
        else:
            raise e
            
    if sql_used:
        sql_used = sql_used.strip()
        # Strip out code markdown formats
        sql_used = re.sub(r"^```sql\s*", "", sql_used, flags=re.IGNORECASE)
        sql_used = re.sub(r"\s*```$", "", sql_used)
        sql_used = sql_used.strip()
        
        # Enforce SQL execution safety
        if not is_select_only(sql_used):
            raise ValueError(f"Blocked query execution of potentially harmful query: {sql_used}")
            
        # Ensure rows are capped to prevent client rendering crashes
        sql_used = enforce_row_limit(sql_used)
        
    return {"answer": answer, "sql": sql_used}

def extract_sql_from_steps(steps):
    """Scrapes query executions from intermediate step agent logs."""
    for action, _ in steps:
        tool_name = getattr(action, "tool", "")
        # Querying commands in sql database agent are usually run via 'sql_db_query'
        if "sql_db_query" in tool_name:
            tool_input = action.tool_input
            if isinstance(tool_input, dict):
                return tool_input.get("query", tool_input.get("sql", str(tool_input)))
            return str(tool_input)
    return None
