# app/streamlit_app.py
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from agent.sql_agent import build_sql_agent, ask, get_available_providers
from viz.chart_intent import get_chart_intent
from viz.chart_builder import build_chart
from db.connection import get_engine

# Load environment variables
load_dotenv()

# Streamlit App Configurations
st.set_page_config(
    page_title="Retail Insights AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom modern stylesheet
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Outfit', sans-serif;
}

/* Custom Gradient Title */
.gradient-title {
    background: linear-gradient(135deg, #818cf8 0%, #c084fc 50%, #f472b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.5rem;
    margin-bottom: 0.2rem;
    letter-spacing: -0.025em;
}

.gradient-subtitle {
    color: #475569;
    font-size: 1.1rem;
    margin-bottom: 2rem;
    font-weight: 300;
}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {
    background-color: #f8fafc !important;
    border-right: 1px solid rgba(0, 0, 0, 0.05);
}

/* Expanders Glassmorphism */
div[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.7) !important;
    border: 1px solid rgba(0, 0, 0, 0.05) !important;
    border-radius: 8px !important;
    margin-bottom: 0.5rem;
}

/* Status Pill Styling */
.status-pill {
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 500;
    display: inline-block;
}
.status-connected {
    background-color: rgba(16, 185, 129, 0.1);
    color: #059669;
    border: 1px solid rgba(52, 211, 153, 0.2);
}
.status-disconnected {
    background-color: rgba(220, 38, 38, 0.1);
    color: #dc2626;
    border: 1px solid rgba(239, 68, 68, 0.2);
}

/* Table info in sidebar */
.table-name-label {
    font-weight: 600;
    color: #4f46e5;
}
.column-name-label {
    font-family: monospace;
    font-size: 0.85rem;
    color: #1e293b;
}
.column-type-label {
    font-family: monospace;
    font-size: 0.8rem;
    color: #64748b;
}

/* Code block customization */
code {
    font-family: 'Fira Code', Consolas, Monaco, monospace !important;
}
</style>
""", unsafe_allow_html=True)

# Helper function to inspect schema
def get_db_tables():
    try:
        engine = get_engine()
        import sqlalchemy as sa
        inspector = sa.inspect(engine)
        return inspector.get_table_names()
    except Exception:
        return []

def get_table_schema(table_name):
    try:
        engine = get_engine()
        import sqlalchemy as sa
        inspector = sa.inspect(engine)
        columns = inspector.get_columns(table_name)
        return [(col['name'], str(col['type'])) for col in columns]
    except Exception:
        return []

# Session State Initialization
if "history" not in st.session_state:
    st.session_state.history = []
if "sql_logs" not in st.session_state:
    st.session_state.sql_logs = []
if "api_key_override" not in st.session_state:
    st.session_state.api_key_override = {}
if "selected_provider" not in st.session_state:
    st.session_state.selected_provider = None

# Sidebar Content
with st.sidebar:
    st.markdown("<h2 style='margin-bottom:0.2rem; color:#f8fafc;'>⚙️ Config & Schema</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 1. API Keys & LLM Settings
    st.markdown("### 🔌 LLM Connection")
    
    available = get_available_providers()
    
    # API key inputs if missing
    if not available and not st.session_state.api_key_override:
        st.warning("No API keys detected in environment. Please input a key below to run the chatbot:")
        key_provider = st.selectbox(
            "API Provider", 
            ["claude", "gemini", "openai"],
            format_func=lambda x: {"claude": "Anthropic", "gemini": "Google", "openai": "OpenAI"}.get(x, x)
        )
        display_name = {"claude": "Anthropic", "gemini": "Google", "openai": "OpenAI"}.get(key_provider, key_provider)
        user_key = st.text_input(f"Enter {display_name} API Key", type="password")
        if user_key:
            env_var_map = {
                "gemini": "GEMINI_API_KEY",
                "claude": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY"
            }
            os.environ[env_var_map[key_provider]] = user_key
            st.session_state.api_key_override[key_provider] = user_key
            st.rerun()
    else:
        # User dropdown to switch providers
        all_keys = list(set(available + list(st.session_state.api_key_override.keys())))
        # Ensure Anthropic is first, then Google, then OpenAI
        sort_order = {"claude": 0, "gemini": 1, "openai": 2}
        all_keys = sorted(all_keys, key=lambda x: sort_order.get(x, 99))
        
        # Format provider names nicely without model names
        provider_names = {
            "claude": "Anthropic",
            "gemini": "Google",
            "openai": "OpenAI"
        }
        
        selected_key = st.selectbox(
            "Active AI Provider", 
            options=all_keys, 
            format_func=lambda x: provider_names.get(x, x),
            index=0 if st.session_state.selected_provider is None else all_keys.index(st.session_state.selected_provider)
        )
        st.session_state.selected_provider = selected_key
        
        # Show connection status
        st.markdown(
            f"<div class='status-pill status-connected'>Connected: {provider_names.get(selected_key, selected_key)}</div>", 
            unsafe_allow_html=True
        )
        
        # Clear chat history button
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🧹 Clear Chat History", use_container_width=True):
            st.session_state.history = []
            st.session_state.sql_logs = []
            if "preview_data" in st.session_state:
                del st.session_state.preview_data
            st.rerun()

    st.markdown("---")
    
    # 2. Database Schema Inspector
    st.markdown("### 🗄️ Database Inspector")
    tables = get_db_tables()
    if not tables:
        st.markdown("<div class='status-pill status-disconnected'>DB Offline</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='status-pill status-connected'>DB Online (retail.db)</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        for table in tables:
            with st.expander(f"📁 {table.capitalize()}"):
                cols = get_table_schema(table)
                # Show columns
                col_df = pd.DataFrame(cols, columns=["Column", "Type"])
                st.dataframe(col_df, hide_index=True, use_container_width=True)
                
                # Table Preview Button
                if st.button(f"Preview {table}", key=f"btn_{table}"):
                    try:
                        engine = get_engine()
                        preview_df = pd.read_sql(f"SELECT * FROM {table} LIMIT 5", engine)
                        st.session_state.preview_data = {"table": table, "df": preview_df}
                    except Exception as e:
                        st.error(f"Error reading preview: {e}")

    # 3. Execution History Log
    st.markdown("---")
    st.markdown("### 📈 SQL Execution Logs")
    if not st.session_state.sql_logs:
        st.info("No queries executed yet.")
    else:
        for idx, log in enumerate(reversed(st.session_state.sql_logs)):
            with st.expander(f"Query #{len(st.session_state.sql_logs) - idx}: {log['question'][:25]}..."):
                st.code(log["sql"], language="sql")
                st.caption(f"Status: Success")


# Main Page Content
st.markdown("<div class='gradient-title'>📊 Retail Insights AI</div>", unsafe_allow_html=True)
st.markdown("<div class='gradient-subtitle'>Talk to your retail database. Ask about revenue, customer segments, sales trends, and products.</div>", unsafe_allow_html=True)

# Show schema table preview if selected
if "preview_data" in st.session_state:
    st.markdown(f"### 🔍 Table Preview: `{st.session_state.preview_data['table']}`")
    st.dataframe(st.session_state.preview_data["df"])
    if st.button("Close Preview"):
        del st.session_state.preview_data
        st.rerun()

# Build SQL Agent
agent = None
provider = st.session_state.selected_provider
db = None

if provider or get_available_providers():
    try:
        agent, active_provider, db = build_sql_agent(provider=provider)
    except Exception as e:
        st.error(f"Error configuring agent: {e}")
else:
    st.info("Please set an API key in the sidebar configuration to begin chatting with the database.")

# Display Chat History
for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.write(turn["content"])
        
        # Display SQL if present and role is assistant
        if turn["role"] == "assistant" and turn.get("sql"):
            with st.expander("🛠️ View SQL Query"):
                st.code(turn["sql"], language="sql")
                
        # Display DataFrame if present
        if turn.get("table") is not None:
            with st.expander("📋 View Data Table", expanded=False):
                st.dataframe(turn["table"], use_container_width=True)
                
        # Display Chart if present
        if turn.get("chart_json") is not None:
            # Rebuild figure from saved intent
            fig = build_chart(turn["table"], turn["chart_json"])
            if fig:
                st.plotly_chart(fig, use_container_width=True)

# Sample question buttons row
st.markdown("💡 **Sample Queries:**")
sample_cols = st.columns(4)
sample_questions = [
    "What were total sales last month?",
    "Which product category generates the most revenue?",
    "Top 5 customers by total spend",
    "How many orders were cancelled this year?"
]

selected_sample = None
for idx, sq in enumerate(sample_questions):
    btn_label = sq
    if len(sq) > 30:
        btn_label = sq[:27] + "..."
    if sample_cols[idx].button(btn_label, key=f"sq_btn_{idx}", help=sq, use_container_width=True, disabled=(agent is None)):
        selected_sample = sq

# Chat Input
chat_input_val = st.chat_input("Ask about sales, customers, products...", disabled=(agent is None))

# Determine final query to execute
question = selected_sample or chat_input_val

if question:
    # Append user chat
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
        
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your retail database..."):
            try:
                # Ask Agent
                result = ask(agent, question)
                st.write(result["answer"])
                
                df = None
                fig = None
                intent = None
                
                # If agent executed a query, query DB to build dataframe
                if result.get("sql"):
                    # Display SQL inside expander
                    with st.expander("🛠️ View SQL Query"):
                        st.code(result["sql"], language="sql")
                    
                    # Fetch results using pandas
                    df = pd.read_sql(result["sql"], db._engine)
                    
                    # Display result table
                    with st.expander("📋 View Data Table", expanded=False):
                        st.dataframe(df, use_container_width=True)
                    
                    # Record log
                    st.session_state.sql_logs.append({
                        "question": question,
                        "sql": result["sql"]
                    })
                    
                    # Check chart intent and build Plotly chart
                    intent = get_chart_intent(question, df, provider=provider)
                    fig = build_chart(df, intent)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                
                # Append assistant history
                st.session_state.history.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sql": result.get("sql"),
                    "table": df,
                    "chart_json": intent
                })
                
                # Force rerun to sync sidebar state query logs
                st.rerun()
                
            except Exception as e:
                error_msg = f"An error occurred during query execution: {e}"
                st.error(error_msg)
                st.session_state.history.append({
                    "role": "assistant",
                    "content": error_msg,
                    "sql": None,
                    "table": None,
                    "chart_json": None
                })
