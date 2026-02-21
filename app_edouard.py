import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import streamlit as st

st.markdown("# Web App d'Edouard")

audio_value = st.audio_input("Record a voice message")

if audio_value:
    st.audio(audio_value)

    data_dir = os.path.join(os.getcwd(), "audio")

    os.makedirs(data_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(data_dir, f"audio_{timestamp}.wav")

    with open(audio_path, "wb") as f:
        f.write(audio_value.getbuffer())

    st.success(f"Audio saved to {audio_path}")