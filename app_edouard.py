import pandas as pd
import plotly.express as px
import ipywidgets as widgets
import os
from datetime import datetime

import streamlit as st

st.markdown(" # Web App d'Edouard")

audio_value = st.audio_input("Record a voice message")

if audio_value:
    st.audio(audio_value)
    
    # Save audio with timestamp
    data_dir = "audio"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir) 
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(data_dir, f"audio_{timestamp}.wav")
    
    with open(audio_path, "wb") as f:
        f.write(audio_value.getbuffer())
    
    st.success(f"Audio saved to {audio_path}")



