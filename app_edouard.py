import streamlit as st
import os
from datetime import datetime

st.title("Uroflow acoustique – Enregistrement audio")

data_dir = "audio"
os.makedirs(data_dir, exist_ok=True)

st.write("Appuyez sur enregistrer puis stop.")

audio = st.audio_input("Enregistrer")

if audio is not None:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(data_dir, f"audio_{timestamp}.wav")

    with open(file_path, "wb") as f:
        f.write(audio.getbuffer())

    st.success(f"Fichier enregistré : {file_path}")

st.divider()
st.subheader("Fichiers enregistrés")

files = sorted(os.listdir(data_dir), reverse=True)

if len(files) == 0:
    st.write("Aucun fichier pour le moment")

else:
    for file in files:
        path = os.path.join(data_dir, file)

        col1, col2 = st.columns([3,1])

        with col1:
            st.audio(path)

        with col2:
            with open(path, "rb") as f:
                st.download_button(
                    "Download",
                    f,
                    file_name=file,
                    mime="audio/wav",
                    key=file
                )