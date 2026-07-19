# viz/chart_builder.py
import plotly.express as px
import plotly.graph_objects as go

def build_chart(df, intent: dict):
    """Builds a customized and styled Plotly figure based on the dataframe and chart intent."""
    if not intent or not intent.get("should_chart"):
        return None

    x = intent.get("x")
    y = intent.get("y")
    color = intent.get("color")
    
    # Validation: Ensure columns exist in DataFrame
    if x and x not in df.columns:
        return None
    if y and y not in df.columns:
        return None
    if color and color not in df.columns:
        color = None # Drop grouping if it is hallucinated

    agg = intent.get("aggregation", "none")
    plot_df = df.copy()
    
    # Perform aggregation if specified
    if agg in ("sum", "avg", "count") and x and y:
        func = {"sum": "sum", "avg": "mean", "count": "count"}[agg]
        plot_df = df.groupby(x, as_index=False)[y].agg(func)

    chart_type = intent.get("chart_type")
    title = intent.get("title", "")
    
    # High-end color scheme: Indigo, Teal, Purple, Pink, Emerald, Amber
    color_sequence = ["#6366f1", "#06b6d4", "#a855f7", "#ec4899", "#10b981", "#f59e0b"]
    
    def apply_theme(fig):
        """Standardizes styling to match the application's premium aesthetic."""
        if fig is None:
            return None
            
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, system-ui, sans-serif", color="#0f172a"),
            title=dict(
                text=f"<b>{title}</b>" if title else "",
                font=dict(size=16, color="#0f172a"),
                x=0.0,
                y=0.95
            ),
            margin=dict(l=40, r=20, t=55, b=40),
            legend=dict(
                bgcolor="rgba(255, 255, 255, 0.6)",
                bordercolor="rgba(0, 0, 0, 0.1)",
                borderwidth=1,
                font=dict(size=11, color="#1e293b")
            ),
            xaxis=dict(
                gridcolor="rgba(0, 0, 0, 0.05)",
                linecolor="rgba(0, 0, 0, 0.1)",
                tickfont=dict(color="#475569")
            ),
            yaxis=dict(
                gridcolor="rgba(0, 0, 0, 0.05)",
                linecolor="rgba(0, 0, 0, 0.1)",
                tickfont=dict(color="#475569")
            )
        )
        return fig

    builders = {
        "bar": lambda: px.bar(plot_df, x=x, y=y, color=color, color_discrete_sequence=color_sequence),
        "line": lambda: px.line(plot_df, x=x, y=y, color=color, color_discrete_sequence=color_sequence, markers=True),
        "pie": lambda: px.pie(plot_df, names=x, values=y, color_discrete_sequence=color_sequence),
        "scatter": lambda: px.scatter(plot_df, x=x, y=y, color=color, color_discrete_sequence=color_sequence),
        "heatmap": lambda: px.density_heatmap(plot_df, x=x, y=y, color_continuous_scale="Viridis"),
    }
    
    try:
        builder = builders.get(chart_type)
        if builder:
            fig = builder()
            return apply_theme(fig)
    except Exception as e:
        print(f"Error building chart of type {chart_type}: {e}")
        return None
        
    return None
