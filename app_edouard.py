import streamlit as st
import os
from datetime import datetime

st.markdown("# Web App d'Edouard")

audio_value = st.audio_input("Record a voice message")

if audio_value:
    st.audio(audio_value)

    # dossier pour enregistrer temporairement le fichier
    data_dir = "audio"
    os.makedirs(data_dir, exist_ok=True)

    # créer un nom unique avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(data_dir, f"audio_{timestamp}.wav")

    # sauvegarde du fichier audio
    with open(audio_path, "wb") as f:
        f.write(audio_value.getbuffer())

    st.success(f"Audio saved to {audio_path}")

    # bouton pour télécharger l'audio sur ton ordinateur
    with open(audio_path, "rb") as f:
        st.download_button(
            label="Download audio",
            data=f,
            file_name=f"audio_{timestamp}.wav",
            mime="audio/wav"
        )