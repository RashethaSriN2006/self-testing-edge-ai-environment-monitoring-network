import streamlit as st
import pandas as pd
import sys
import os

# Add src folder
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from predict import assess


# Page settings
st.set_page_config(
    page_title="SentriEnv",
    layout="wide"
)

# Title
st.title("SentriEnv")
st.subheader("AI-Powered Environmental Risk Monitoring")

st.write(
    "Enter sensor readings to predict environmental risk "
    "and check sensor reliability."
)

st.divider()


# Sensor inputs
col1, col2, col3 = st.columns(3)

with col1:
    temp = st.number_input(
        "Temperature (°C)",
        0.0, 60.0, 30.0
    )

    hum = st.number_input(
        "Humidity (%)",
        0.0, 100.0, 60.0
    )

    rain = st.number_input(
        "Rainfall (mm)",
        0.0, 1000.0, 100.0
    )


with col2:
    water = st.number_input(
        "Water Level",
        0.0, 100.0, 20.0
    )

    air = st.number_input(
        "Air Quality",
        0.0, 500.0, 120.0
    )


with col3:
    soil = st.number_input(
        "Soil Moisture (%)",
        0.0, 100.0, 35.0
    )

    vib = st.number_input(
        "Vibration",
        0.0, 30.0, 5.0
    )


st.divider()


# Analyze button
if st.button("Analyze Environment", use_container_width=True):

    reading = {
        "temp": temp,
        "hum": hum,
        "rain": rain,
        "water": water,
        "air": air,
        "soil": soil,
        "vib": vib
    }

    # AI prediction
    result = assess(reading)

    risk = result["risk"]
    confidence = result["confidence"]

    # Risk result
    st.subheader("🚨 Environmental Risk")

    if risk == "SAFE":
        st.success(
            f"🟢 SAFE — Confidence: {confidence:.1%}"
        )

    elif risk == "WARNING":
        st.warning(
            f"🟡 WARNING — Confidence: {confidence:.1%}"
        )

    else:
        st.error(
            f"🔴 CRITICAL — Confidence: {confidence:.1%}"
        )


    # Trusted sensors
    st.subheader("Sensor Reliability")

    st.metric(
        "Trusted Sensors",
        f"{result['trusted_sensors']} / 7"
    )


    # Sensor trust
    st.subheader("Sensor Trust")

    trust = result["trust"]

    cols = st.columns(4)

    for i, (sensor, value) in enumerate(trust.items()):

        with cols[i % 4]:

            st.metric(
                sensor.upper(),
                f"{value:.2f}"
            )

            if value >= 0.5:
                st.caption("Healthy")
            else:
                st.caption("⚠️ Low Trust")


    # Trust chart
    st.subheader("Sensor Trust Chart")

    trust_df = pd.DataFrame({
        "Sensor": list(trust.keys()),
        "Trust": list(trust.values())
    })

    st.bar_chart(
        trust_df.set_index("Sensor")
    )


    # Sensor status table
    st.subheader("📋 Sensor Status")

    status_data = []

    for sensor, value in trust.items():

        if value >= 0.5:
            status = "Healthy"
        else:
            status = "Low Trust"

        status_data.append({
            "Sensor": sensor.upper(),
            "Trust Score": value,
            "Status": status
        })

    status_df = pd.DataFrame(status_data)

    st.dataframe(
        status_df,
        use_container_width=True
    )