import pandas as pd
import plotly.express as px
import ipywidgets as widgets

import streamlit as st

st.markdown(" # Web App d'Edouard")

audio_value = st.audio_input("Record a voice message")

if audio_value:
    st.audio(audio_value)

