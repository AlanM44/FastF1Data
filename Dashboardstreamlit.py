pip install plotly
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import streamlit as st

# ----- Streamlit Config -----
st.set_page_config(layout="wide", page_title="F1 2025 Dashboard")
st.title("F1 2025 Driver Performance Dashboard")

# ----- Database Connection -----
user     = os.getenv("F1_DB_USER", "root")
password = os.getenv("F1_DB_PASS", "")
host     = "localhost"
port     = 3306
database = "fastf1"
pw_esc   = quote_plus(password)
engine = create_engine(f"mysql+mysqlconnector://{user}:{pw_esc}@{host}:{port}/{database}")

# ----- Load Drivers and Teams -----
st.cache_data(ttl=3600)
def load_driver_team_data():
    query = """
    SELECT rr.code, t.name AS team
    FROM race_results rr
    JOIN teams t ON rr.team_id = t.team_id
    GROUP BY rr.code, t.name;
    """
    return pd.read_sql(query, con=engine)

driver_team_df = load_driver_team_data()
driver_to_team = dict(zip(driver_team_df['code'], driver_team_df['team']))

# ----- Points Progression Over Races -----
st.subheader("Points Progression Over Races")
query_progression = """
SELECT r.round, r.event_name, rr.code, rr.points, t.name AS team
FROM race_results rr
JOIN races r ON rr.race_id = r.race_id
JOIN teams t ON rr.team_id = t.team_id
ORDER BY r.round, rr.code;
"""
df = pd.read_sql(query_progression, con=engine)
df['points'] = df['points'].fillna(0)
df = df.sort_values(['code', 'round'])
df['cum_points'] = df.groupby('code')['points'].cumsum()

# Get ordered list of event names
event_order = df[['round', 'event_name']].drop_duplicates().sort_values('round')
ordered_events = event_order['event_name'].tolist()

# Team filter
teams = sorted(df['team'].unique())
selected_teams = st.multiselect("Filter by Team", teams, default=teams)
df = df[df['team'].isin(selected_teams)]

# Pivot table for plotting
pivot_df = (
    df.pivot(index='event_name', columns='code', values='cum_points')
      .reindex(ordered_events)
)

# ----- Total Points by Driver -----
st.subheader("Total Points by Driver")
df_total = df.groupby(['code']).agg({'points': 'sum'}).reset_index()
df_total['team'] = df_total['code'].map(driver_to_team)

fig1 = px.bar(df_total, x='code', y='points', title="F1 2025: Total Driver Points",
              labels={'code': 'Driver Code', 'points': 'Total Points'},
              text='points', color='team')
fig1.update_traces(textposition='outside')
fig1.update_layout(xaxis_title='Driver Code', yaxis_title='Total Points')
st.plotly_chart(fig1, use_container_width=True)

fig2 = go.Figure()
for driver in pivot_df.columns:
    fig2.add_trace(go.Scatter(x=pivot_df.index, y=pivot_df[driver], mode='lines+markers', name=driver))

fig2.update_layout(
    title="F1 2025: Driver Points Progression by Race",
    xaxis_title="Race",
    yaxis_title="Cumulative Points",
    xaxis=dict(tickangle=90),
    legend_title="Driver Code",
    hovermode="x unified"
)

st.plotly_chart(fig2, use_container_width=True)

# ----- Filter and Table -----
st.subheader("Explore Driver Data")
driver_filter = st.selectbox("Select a Driver Code", sorted(df['code'].unique()))
df_driver = df[df['code'] == driver_filter][['round', 'event_name', 'points', 'cum_points']]
st.dataframe(df_driver.reset_index(drop=True))

# ----- Driver Comparison Chart -----
st.subheader("Compare Drivers")
selected_drivers = st.multiselect("Choose Drivers to Compare", sorted(df['code'].unique()), default=sorted(df['code'].unique())[:3])

fig3 = go.Figure()
for driver in selected_drivers:
    if driver in pivot_df.columns:
        fig3.add_trace(go.Scatter(
            x=pivot_df.index,
            y=pivot_df[driver],
            mode='lines+markers',
            name=driver
        ))

fig3.update_layout(
    title="Driver Comparison: Cumulative Points by Race",
    xaxis_title="Race",
    yaxis_title="Cumulative Points",
    xaxis=dict(tickangle=90),
    legend_title="Driver Code",
    hovermode="x unified"
)

st.plotly_chart(fig3, use_container_width=True)
