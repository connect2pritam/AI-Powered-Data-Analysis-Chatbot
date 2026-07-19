# tests/test_chart_builder.py
import pandas as pd
import plotly.graph_objects as go
from viz.chart_builder import build_chart

# Create dummy dataframe for testing
test_df = pd.DataFrame({
    "Category": ["Laptops", "Smartphones", "Accessories", "Laptops"],
    "Revenue": [15000.0, 24000.0, 8000.0, 10000.0],
    "Units": [15, 30, 80, 10]
})

def test_build_chart_disabled():
    intent = {
        "should_chart": False,
        "chart_type": "bar",
        "x": "Category",
        "y": "Revenue"
    }
    fig = build_chart(test_df, intent)
    assert fig is None

def test_build_chart_invalid_column():
    intent = {
        "should_chart": True,
        "chart_type": "bar",
        "x": "NonExistentColumn",
        "y": "Revenue"
    }
    fig = build_chart(test_df, intent)
    assert fig is None

def test_build_chart_bar():
    intent = {
        "should_chart": True,
        "chart_type": "bar",
        "x": "Category",
        "y": "Revenue",
        "aggregation": "none",
        "title": "Category Revenue"
    }
    fig = build_chart(test_df, intent)
    assert fig is not None
    assert isinstance(fig, go.Figure)
    assert fig.layout.title.text == "<b>Category Revenue</b>"

def test_build_chart_aggregation():
    intent = {
        "should_chart": True,
        "chart_type": "bar",
        "x": "Category",
        "y": "Revenue",
        "aggregation": "sum",
        "title": "Category Total Revenue"
    }
    fig = build_chart(test_df, intent)
    assert fig is not None
    assert isinstance(fig, go.Figure)
    
    # Verify the trace has aggregated Laptop sales (15000 + 10000 = 25000)
    # The figure data will hold the aggregated dataframe values
    # Let's extract the data used in the figure
    trace_x = fig.data[0].x
    trace_y = fig.data[0].y
    
    # Find Category laptops index
    laptop_idx = list(trace_x).index("Laptops")
    assert trace_y[laptop_idx] == 25000.0
