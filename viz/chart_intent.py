# viz/chart_intent.py
import json
import re
from agent.sql_agent import get_llm
from agent.prompts import build_chart_intent_prompt

def get_chart_intent(user_question, df, provider=None):
    """Sends user query and dataframe schema to the LLM to get a structured charting intent."""
    if df is None or df.empty:
        return {"should_chart": False, "chart_type": "none"}
        
    llm, _ = get_llm(provider=provider, temperature=0)
    if not llm:
        return {"should_chart": False, "chart_type": "none"}
        
    # Keep data payload lightweight by only sending columns, types, and top 5 rows
    prompt = build_chart_intent_prompt(
        user_question,
        list(df.columns),
        {c: str(df[c].dtype) for c in df.columns},
        df.head(5).to_dict(orient="records"),
    )
    
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # Strip potential markdown fences
        content = re.sub(r"^```json\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"^```\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        content = content.strip()
        
        intent = json.loads(content)
        # Ensure schema compliance
        if "should_chart" not in intent:
            intent["should_chart"] = False
        return intent
    except Exception as e:
        print(f"Error parsing chart intent: {e}")
        return {"should_chart": False, "chart_type": "none"}
