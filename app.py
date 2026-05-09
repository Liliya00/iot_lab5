import requests
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium


STORE_API_URL = "http://127.0.0.1:8000/processed_agent_data/"


st.set_page_config(
    page_title="Road Vision MapView",
    page_icon="🗺️",
    layout="wide"
)


def get_marker_color(road_state: str) -> str:
    state = str(road_state).lower()

    if state == "good":
        return "green"
    if state == "uneven":
        return "orange"
    if state == "pothole":
        return "red"

    return "blue"


def load_from_csv() -> pd.DataFrame:
    return pd.read_csv("data/road_data.csv")


def load_from_store() -> pd.DataFrame:
    response = requests.get(STORE_API_URL, timeout=5)
    response.raise_for_status()

    data = response.json()

    rows = []
    for item in data:
        if "agent_data" in item:
            agent_data = item["agent_data"]
            accelerometer = agent_data.get("accelerometer", {})
            gps = agent_data.get("gps", {})

            rows.append({
                "id": item.get("id"),
                "road_state": item.get("road_state"),
                "x": accelerometer.get("x"),
                "y": accelerometer.get("y"),
                "z": accelerometer.get("z"),
                "latitude": gps.get("latitude"),
                "longitude": gps.get("longitude"),
                "timestamp": agent_data.get("timestamp")
            })
        else:
            rows.append({
                "id": item.get("id"),
                "road_state": item.get("road_state"),
                "x": item.get("x"),
                "y": item.get("y"),
                "z": item.get("z"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "timestamp": item.get("timestamp")
            })

    return pd.DataFrame(rows)


def create_map(df: pd.DataFrame):
    df = df.dropna(subset=["latitude", "longitude"])

    # Якщо координати переплутані місцями, автоматично міняємо їх
    mask = (df["latitude"] < 40) & (df["longitude"] > 40)

    df.loc[mask, ["latitude", "longitude"]] = df.loc[
        mask, ["longitude", "latitude"]
    ].values

    if df.empty:
        return folium.Map(location=[30.52, 50.45], zoom_start=13)

    center_lat = df["latitude"].mean()
    center_lon = df["longitude"].mean()

    road_map = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    for _, row in df.iterrows():
        road_state = row.get("road_state", "unknown")
        color = get_marker_color(road_state)

        popup_text = f"""
        <b>Road state:</b> {road_state}<br>
        <b>Accelerometer:</b> x={row.get("x")}, y={row.get("y")}, z={row.get("z")}<br>
        <b>Latitude:</b> {row.get("latitude")}<br>
        <b>Longitude:</b> {row.get("longitude")}<br>
        <b>Timestamp:</b> {row.get("timestamp")}
        """

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=8,
            popup=folium.Popup(popup_text, max_width=350),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75
        ).add_to(road_map)

    return road_map


st.title("Road Vision MapView")
st.write(
    "MapView відображає стан дорожнього покриття на основі даних з CSV-файлу або Store API."
)

source = st.sidebar.radio(
    "Оберіть джерело даних:",
    ["CSV файл", "Store API"]
)

if source == "CSV файл":
    df = load_from_csv()
    st.sidebar.success("Дані завантажено з CSV")
else:
    try:
        df = load_from_store()
        st.sidebar.success("Дані завантажено зі Store API")
    except Exception as e:
        st.sidebar.error(f"Не вдалося отримати дані зі Store API: {e}")
        df = load_from_csv()
        st.sidebar.info("Показано резервні дані з CSV")

# Обмежуємо кількість точок для карти, щоб Streamlit не зависав
if len(df) > 1000:
    df_for_map = df.tail(1000)
else:
    df_for_map = df

st.subheader("Карта стану дорожнього покриття")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Кількість точок", len(df))

with col2:
    potholes = len(df[df["road_state"].astype(str).str.lower() == "pothole"])
    st.metric("Виявлено ям", potholes)

with col3:
    good = len(df[df["road_state"].astype(str).str.lower() == "good"])
    st.metric("Нормальний стан", good)

road_map = create_map(df_for_map)
st.info(f"На карті показано {len(df_for_map)} останніх точок із {len(df)} записів.")
st_folium(road_map, width=None, height=550)

st.subheader("Дані")
st.dataframe(df, use_container_width=True)