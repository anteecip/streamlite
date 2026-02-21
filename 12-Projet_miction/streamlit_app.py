'''Commande bash de lancement :
streamlit run streamlit_app.py
'''

# ===========================================================
# streamlit_app.py - Acoustic Uroflowmetry POC local
# ===========================================================

import streamlit as st
import numpy as np
import tempfile
import joblib
import soundfile as sf
import matplotlib.pyplot as plt
import pandas as pd

from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
from dsp_functions import analyze_recording

st.set_page_config(layout="wide")
st.title("🚽 Acoustic Uroflowmetry — Microphone Live")

# ===========================================================
# Chargement du modèle calibré (KNN + scaler)
# ===========================================================
MODEL_PATH = "uroflow_knn_model.pkl"

@st.cache_resource
def load_model(path):
    model = joblib.load(path)
    return model["nn"], model["y_calib"], model["weights"], model["scaler"]

nn, y_calib, weights, scaler = load_model(MODEL_PATH)

# ===========================================================
# Classe pour buffer audio via micro
# ===========================================================
class AudioRecorder(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv(self, frame):
        audio = frame.to_ndarray().flatten()
        self.frames.append(audio)
        return frame

    def get_audio(self):
        if len(self.frames) == 0: 
            return None
        return np.concatenate(self.frames)

# ===========================================================
# Paramètres utilisateur
# ===========================================================
mode = st.radio(
    "Mode d'analyse",
    ["Segment (débit constant par phase)", "Fine (mesure toutes les X secondes)"]
)
fine_step = st.slider("Pas de mesure fine (secondes)", 0.1, 1.0, 0.2, 0.1)

st.markdown("### 🎤 Enregistrement micro")
ctx = webrtc_streamer(key="uroflow", mode=WebRtcMode.SENDONLY,
                      audio_processor_factory=AudioRecorder,
                      media_stream_constraints={"audio": True, "video": False})

if st.button("⏹️ Stop et analyser"):
    if ctx.audio_processor:
        audio_data = ctx.audio_processor.get_audio()
        if audio_data is None:
            st.warning("Aucun son capturé")
            st.stop()

        # Sauvegarde temporaire du .wav
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        sf.write(temp_wav.name, audio_data, 48000)
        st.success("🔎 Analyse du signal...")

        # =========================
        # Analyse du fichier avec scaler
        # =========================
        results = analyze_recording(
            temp_wav.name,
            nn,
            y_calib,
            weights,
            scaler=scaler,        # <-- scaler appliqué ici
            mode="segment" if mode=="Segment (débit constant par phase)" else "fine",
            measure_step=fine_step
        )

        # Affichage tableau
        df = pd.DataFrame(results)
        st.dataframe(df)

        # Affichage courbe débit
        times, flows = [], []
        t = 0
        for r in results:
            times.append(t)
            flows.append(r["debit"])
            t += r["duree"]

        fig, ax = plt.subplots(figsize=(10,4))
        ax.step(times, flows, where='post')
        ax.set_xlabel("Temps (s)")
        ax.set_ylabel("Débit (ml/s)")
        ax.set_title("Courbe de débit estimé")
        ax.grid(True)
        st.pyplot(fig)

        # Indicateurs principaux
        total_time = sum(df["duree"])
        total_volume = sum(df["debit"] * df["duree"])
        mean_flow = total_volume / total_time
        qmax = df["debit"].max()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Temps total (s)", round(total_time, 2))
        c2.metric("Volume (ml)", round(total_volume, 2))
        c3.metric("Débit moyen (ml/s)", round(mean_flow, 2))
        c4.metric("Qmax (ml/s)", round(qmax, 2))
