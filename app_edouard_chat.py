import streamlit as st
import os
from datetime import datetime
import numpy as np
import librosa
import soundfile as sf

st.title("Uroflow acoustique – Enregistrement audio")

# dossier de stockage serveur
data_dir = "audio"
os.makedirs(data_dir, exist_ok=True)


# ===============================
# Correction AGC robuste
# ===============================
def correct_agc_robust(
    input_path,
    output_path,
    frame_length=2048,
    hop_length=512,
    agc_sensitivity=2.5,
    agc_gain_limit=4.0,
    min_agc_duration=0.5
):

    y, sr = librosa.load(input_path, sr=None, mono=True)

    rms = librosa.feature.rms(
        y=y,
        frame_length=frame_length,
        hop_length=hop_length
    )[0]

    diff = np.diff(rms)

    threshold = -np.std(diff) * agc_sensitivity
    candidates = np.where(diff < threshold)[0]

    agc_frame = None
    min_frames = int((min_agc_duration * sr) / hop_length)

    for c in candidates:
        if c > 20 and c + min_frames < len(rms):

            pre = np.median(rms[c-20:c])
            post = np.median(rms[c:c+min_frames])

            drop_ratio = post / (pre + 1e-8)

            if drop_ratio < 0.65:
                agc_frame = c
                break

    if agc_frame is not None:

        agc_sample = agc_frame * hop_length

        ref_start = int(max(0, agc_sample - sr * 1.5))
        ref_end = agc_sample
        ref_segment = y[ref_start:ref_end]

        rms_ref = np.sqrt(np.mean(ref_segment**2)) + 1e-8
        rms_post = np.sqrt(np.mean(y[agc_sample:]**2)) + 1e-8

        gain = rms_ref / rms_post
        gain = min(gain, agc_gain_limit)

        y_corrected = y.copy()
        y_corrected[agc_sample:] *= gain

    else:
        y_corrected = y

    y_corrected = np.clip(y_corrected, -1, 1)

    sf.write(output_path, y_corrected, sr)

    return agc_frame is not None


# ===============================
# Enregistrement audio
# ===============================
st.write("Appuyez sur enregistrer puis stop.")

audio = st.audio_input("Enregistrer (format WAV)")

if audio is not None:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    raw_path = os.path.join(data_dir, f"uroflow_raw_{timestamp}.wav")
    processed_path = os.path.join(data_dir, f"uroflow_corrected_{timestamp}.wav")

    # sauvegarde WAV brut
    with open(raw_path, "wb") as f:
        f.write(audio.getbuffer())

    # correction AGC
    agc_detected = correct_agc_robust(
        raw_path,
        processed_path
    )

    st.success("Enregistrement terminé")

    st.write("AGC détecté :", agc_detected)

    st.audio(processed_path)

    # téléchargement du fichier corrigé
    with open(processed_path, "rb") as f:
        st.download_button(
            label="Télécharger le WAV corrigé",
            data=f,
            file_name=os.path.basename(processed_path),
            mime="audio/wav"
        )


# ===============================
# Historique fichiers
# ===============================
st.divider()
st.subheader("Fichiers enregistrés")

files = sorted(os.listdir(data_dir), reverse=True)

if len(files) == 0:
    st.write("Aucun fichier pour le moment")

else:
    for file in files:

        path = os.path.join(data_dir, file)

        col1, col2 = st.columns([3, 1])

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