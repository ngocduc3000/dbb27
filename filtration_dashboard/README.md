# 💧 Filtration System Monitoring Dashboard

A real-time dashboard for monitoring body/filtration system parameters with simulated sensor data, alerts, and historical trends.

## Features

- **Real-time Monitoring**: Live updates of key filtration parameters
- **Interactive Charts**: Historical trends using Plotly
- **Alert System**: Automatic detection of abnormal conditions
- **Status Indicators**: Clear visual system health display
- **Configurable Settings**: Adjustable update intervals and display options

## Monitored Parameters

- **Flow Rate** (mL/min) - Fluid flow through the filter
- **Inlet Pressure** (mmHg) - Pressure before filtration
- **Outlet Pressure** (mmHg) - Pressure after filtration  
- **Temperature** (°C) - System operating temperature
- **Filter Efficiency** (%) - Effectiveness of filtration process
- **Pressure Drop** (mmHg) - Difference between inlet/outlet pressure

## System Status Levels

- **🟢 Normal**: All parameters within expected ranges
- **🟡 Warning**: One or more parameters outside normal range
- **🔴 Critical**: Severe deviation requiring immediate attention

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the dashboard:
```bash
streamlit run streamlit_app.py
```

The dashboard will open in your default web browser at http://localhost:8501

## Controls

- **Update Interval**: Set how often new data is generated (2-30 seconds)
- **Auto-refresh**: Enable/disable automatic data updates
- **Display Options**: Toggle historical charts and alert log visibility
- **Manual Refresh**: Click to force immediate data update

## Data Simulation

The dashboard simulates realistic filtration system behavior including:
- Normal parameter variations
- Occasional anomalies and spikes
- Correlated parameter relationships (e.g., pressure drop affecting efficiency)
- Random fault simulations for demonstration purposes

## Customization

To adapt for real sensor data:
1. Replace the `generate_sensor_data()` function with actual sensor readings
2. Modify threshold values in the status checking logic
3. Adjust units and labels as needed for your specific filtration system

## Requirements

- Python 3.7+
- Streamlit
- Pandas
- NumPy
- Plotly

See `requirements.txt` for specific versions.

## Notes

⚠️ **Disclaimer**: This dashboard uses simulated data for demonstration purposes. For medical or critical industrial applications, replace with actual sensor data and validate all alarm thresholds with qualified personnel.

---
*Generated as a complete, ready-to-use filtration system monitoring solution*