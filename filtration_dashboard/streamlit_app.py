import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page configuration
st.set_page_config(
    page_title="Filtration System Dashboard",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for data storage
if 'data_history' not in st.session_state:
    st.session_state.data_history = pd.DataFrame(columns=[
        'timestamp', 'flow_rate', 'inlet_pressure', 'outlet_pressure', 
        'temperature', 'efficiency', 'status'
    ])
    
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# Simulation parameters
NORMAL_FLOW = 300  # mL/min
NORMAL_INLET_PRESSURE = 250  # mmHg
NORMAL_OUTLET_PRESSURE = 50  # mmHg
NORMAL_TEMP = 37.0  # °C
NORMAL_EFFICIENCY = 95.0  # %

def generate_sensor_data():
    """Generate realistic filtration system sensor data with occasional anomalies"""
    timestamp = datetime.now()
    
    # Base normal values with small random variations
    flow_rate = NORMAL_FLOW + np.random.normal(0, 15)
    inlet_pressure = NORMAL_INLET_PRESSURE + np.random.normal(0, 10)
    outlet_pressure = NORMAL_OUTLET_PRESSURE + np.random.normal(0, 5)
    temperature = NORMAL_TEMP + np.random.normal(0, 0.5)
    
    # Efficiency inversely related to pressure drop (simplified model)
    pressure_drop = inlet_pressure - outlet_pressure
    base_efficiency = NORMAL_EFFICIENCY - (pressure_drop - 200) * 0.1
    efficiency = max(70, min(99, base_efficiency + np.random.normal(0, 1.5)))
    
    # Determine system status
    status = "Normal"
    alerts = []
    
    # Check for abnormal conditions
    if flow_rate < 200 or flow_rate > 400:
        status = "Warning"
        alerts.append(f"Flow rate abnormal: {flow_rate:.1f} mL/min")
    
    if inlet_pressure > 350 or inlet_pressure < 150:
        status = "Warning" 
        alerts.append(f"Inlet pressure abnormal: {inlet_pressure:.1f} mmHg")
        
    if temperature > 38.5 or temperature < 35.5:
        status = "Warning"
        alerts.append(f"Temperature abnormal: {temperature:.1f} °C")
        
    if efficiency < 85:
        status = "Critical"
        alerts.append(f"Filter efficiency low: {efficiency:.1f}%")
        
    # Random occasional spikes (5% chance)
    if np.random.random() < 0.05:
        anomaly_type = np.random.choice(['flow', 'pressure', 'temp', 'efficiency'])
        if anomaly_type == 'flow':
            flow_rate *= np.random.choice([0.5, 1.8])
            alerts.append(f"Sudden flow change detected!")
        elif anomaly_type == 'pressure':
            inlet_pressure *= np.random.choice([0.6, 2.0])
            alerts.append(f"Pressure spike detected!")
        elif anomaly_type == 'temp':
            temperature += np.random.choice([-3, 4])
            alerts.append(f"Temperature excursion!")
        else:
            efficiency *= np.random.choice([0.7, 0.8])
            alerts.append(f"Efficiency drop!")
            
    # Add alerts to session state
    for alert in alerts:
        if alert not in [a['message'] for a in st.session_state.alerts[-10:]]:  # Avoid duplicates
            st.session_state.alerts.append({
                'timestamp': timestamp,
                'message': alert,
                'level': 'Warning' if 'Warning' in status else 'Critical'
            })
    
    # Keep only last 50 alerts
    if len(st.session_state.alerts) > 50:
        st.session_state.alerts = st.session_state.alerts[-50:]
        
    return {
        'timestamp': timestamp,
        'flow_rate': max(0, flow_rate),
        'inlet_pressure': max(0, inlet_pressure),
        'outlet_pressure': max(0, outlet_pressure),
        'temperature': temperature,
        'efficiency': efficiency,
        'status': status
    }

def update_data():
    """Add new data point to history"""
    new_data = generate_sensor_data()
    st.session_state.data_history = pd.concat([
        st.session_state.data_history, 
        pd.DataFrame([new_data])
    ], ignore_index=True)
    
    # Keep only last 1000 points (about 100 minutes at 6-second intervals)
    if len(st.session_state.data_history) > 1000:
        st.session_state.data_history = st.session_state.data_history.iloc[-1000:]

# Sidebar controls
st.sidebar.title("⚙️ Dashboard Controls")
st.sidebar.subheader("Simulation Settings")

update_interval = st.sidebar.slider(
    "Update interval (seconds)", 
    min_value=2, 
    max_value=30, 
    value=5,
    help="How often to generate new sensor data"
)

st.sidebar.subheader("Display Options")
show_historical = st.sidebar.checkbox("Show historical trends", value=True)
show_alerts = st.sidebar.checkbox("Show alert log", value=True)
auto_scroll = st.sidebar.checkbox("Auto-scroll charts", value=True)

# Manual refresh button
if st.sidebar.button("🔄 Refresh Data Now"):
    update_data()
    st.rerun()

# Auto-refresh mechanism
if st.sidebar.checkbox("Enable auto-refresh", value=True):
    time.sleep(update_interval)
    update_data()
    st.rerun()

# Main dashboard header
st.title("💧 Real-time Filtration System Monitoring Dashboard")
st.markdown("---")

# Current status indicators
col1, col2, col3, col4 = st.columns(4)

latest_data = st.session_state.data_history.iloc[-1] if len(st.session_state.data_history) > 0 else None

if latest_data is not None:
    # Status color
    status_colors = {
        "Normal": "green",
        "Warning": "orange", 
        "Critical": "red"
    }
    status_color = status_colors.get(latest_data['status'], "gray")
    
    with col1:
        st.metric(
            label="System Status",
            value=latest_data['status'],
            delta=None
        )
        st.markdown(f"<p style='color: {status_color}; font-size: 20px;'>{latest_data['status']}</p>", 
                   unsafe_allow_html=True)
    
    with col2:
        st.metric(
            label="Flow Rate", 
            value=f"{latest_data['flow_rate']:.0f} mL/min",
            delta=f"{latest_data['flow_rate'] - NORMAL_FLOW:+.0f}"
        )
    
    with col3:
        st.metric(
            label="Inlet Pressure",
            value=f"{latest_data['inlet_pressure']:.0f} mmHg",
            delta=f"{latest_data['inlet_pressure'] - NORMAL_INLET_PRESSURE:+.0f}"
        )
    
    with col4:
        st.metric(
            label="Outlet Pressure", 
            value=f"{latest_data['outlet_pressure']:.0f} mmHg",
            delta=f"{latest_data['outlet_pressure'] - NORMAL_OUTLET_PRESSURE:+.0f}"
        )

# Second row of metrics
col5, col6, col7, col8 = st.columns(4)

if latest_data is not None:
    with col5:
        st.metric(
            label="Temperature",
            value=f"{latest_data['temperature']:.1f} °C",
            delta=f"{latest_data['temperature'] - NORMAL_TEMP:+.1f}"
        )
    
    with col6:
        st.metric(
            label="Filter Efficiency",
            value=f"{latest_data['efficiency']:.1f}%",
            delta=f"{latest_data['efficiency'] - NORMAL_EFFICIENCY:+.1f}"
        )
    
    with col7:
        pressure_drop = latest_data['inlet_pressure'] - latest_data['outlet_pressure']
        st.metric(
            label="Pressure Drop",
            value=f"{pressure_drop:.0f} mmHg"
        )
    
    with col8:
        st.metric(
            label="Data Points",
            value=len(st.session_state.data_history)
        )

# Charts section
if show_historical and len(st.session_state.data_history) > 1:
    st.markdown("---")
    st.subheader("📊 Historical Trends")
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Flow Rate (mL/min)', 'Pressures (mmHg)', 
                       'Temperature (°C)', 'Filter Efficiency (%)'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    df = st.session_state.data_history.copy()
    
    # Flow rate
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['flow_rate'], 
                  name="Flow Rate", line=dict(color='blue')),
        row=1, col=1
    )
    fig.add_hline(y=NORMAL_FLOW, line_dash="dash", line_color="gray", row=1, col=1)
    
    # Pressures
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['inlet_pressure'], 
                  name="Inlet Pressure", line=dict(color='red')),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['outlet_pressure'], 
                  name="Outlet Pressure", line=dict(color='green')),
        row=1, col=2
    )
    fig.add_hline(y=NORMAL_INLET_PRESSURE, line_dash="dash", line_color="red", row=1, col=2)
    fig.add_hline(y=NORMAL_OUTLET_PRESSURE, line_dash="dash", line_color="green", row=1, col=2)
    
    # Temperature
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['temperature'], 
                  name="Temperature", line=dict(color='orange')),
        row=2, col=1
    )
    fig.add_hline(y=NORMAL_TEMP, line_dash="dash", line_color="gray", row=2, col=1)
    
    # Efficiency
    fig.add_trace(
        go.Scatter(x=df['timestamp'], y=df['efficiency'], 
                  name="Efficiency", line=dict(color='purple')),
        row=2, col=2
    )
    fig.add_hline(y=NORMAL_EFFICIENCY, line_dash="dash", line_color="gray", row=2, col=2)
    
    # Update layout
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="Filtration System Parameters Over Time"
    )
    
    # Update axes labels
    fig.update_yaxes(title_text="mL/min", row=1, col=1)
    fig.update_yaxes(title_text="mmHg", row=1, col=2)
    fig.update_yaxes(title_text="°C", row=2, col=1)
    fig.update_yaxes(title_text="%", row=2, col=2)
    
    st.plotly_chart(fig, use_container_width=True)

# Alert section
if show_alerts and len(st.session_state.alerts) > 0:
    st.markdown("---")
    st.subheader("🚨 Alert Log")
    
    alerts_df = pd.DataFrame(st.session_state.alerts)
    alerts_df = alerts_df.sort_values('timestamp', ascending=False)
    
    # Format for display
    display_df = alerts_df[['timestamp', 'message', 'level']].copy()
    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%H:%M:%S')
    display_df.columns = ['Time', 'Alert Message', 'Level']
    
    # Color code by level
    def color_level(val):
        if val == 'Critical':
            return 'background-color: #ffcccc'
        elif val == 'Warning':
            return 'background-color: #fff2cc'
        else:
            return ''
    
    styled_df = display_df.style.applymap(color_level, subset=['Level'])
    st.dataframe(styled_df, use_container_width=True, height=300)

# System info
st.markdown("---")
st.caption(
    f"Filtration System Dashboard | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    f"Simulating body filtration system data | "
    f"Generated {len(st.session_state.data_history)} data points"
)