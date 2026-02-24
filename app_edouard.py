import streamlit as st
import os
from datetime import datetime
import numpy as np
import librosa
import soundfile as sf

st.title("Uroflow acoustique – Enregistrement audio")

data_dir = "audio"
os.makedirs(data_dir, exist_ok=True)


# ===============================
# Correction AGC robuste + diagnostic
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

    diagnostic = {
        "agc_detected": False,
        "agc_time_sec": None,
        "rms_before": None,
        "rms_after": None,
        "gain_applied": None
    }

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

        diagnostic["agc_detected"] = True
        diagnostic["agc_time_sec"] = agc_sample / sr
        diagnostic["rms_before"] = float(rms_ref)
        diagnostic["rms_after"] = float(rms_post)
        diagnostic["gain_applied"] = float(gain)

    else:
        y_corrected = y

    y_corrected = np.clip(y_corrected, -1, 1)

    sf.write(output_path, y_corrected, sr)

    return diagnostic


# ===============================
# Enregistrement audio
# ===============================
st.write("Appuyez sur enregistrer puis stop.")

audio = st.audio_input("Enregistrer (WAV)")

if audio is not None:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    raw_path = os.path.join(data_dir, f"temp_raw.wav")
    processed_path = os.path.join(data_dir, f"uroflow_{timestamp}.wav")

    # on écrase toujours le brut (temporaire)
    with open(raw_path, "wb") as f:
        f.write(audio.getbuffer())

    diagnostic = correct_agc_robust(
        raw_path,
        processed_path
    )

    st.success("Enregistrement terminé")

    # Lecture audio corrigé
    st.audio(processed_path)

    # ===============================
    # Diagnostic AGC
    # ===============================
    st.subheader("Diagnostic AGC")

    if diagnostic["agc_detected"]:

        st.write("AGC détecté")
        st.write(f"Moment AGC : {diagnostic['agc_time_sec']:.2f} secondes")
        st.write(f"Niveau avant AGC (RMS) : {diagnostic['rms_before']:.5f}")
        st.write(f"Niveau après AGC (RMS) : {diagnostic['rms_after']:.5f}")
        st.write(f"Gain appliqué : {diagnostic['gain_applied']:.2f}")

    else:
        st.write("Aucun AGC détecté")

    # ===============================
    # Téléchargement unique
    # ===============================
    with open(processed_path, "rb") as f:
        st.download_button(
            label="Télécharger le dernier fichier corrigé",
            data=f,
            file_name=os.path.basename(processed_path),
            mime="audio/wav"
        )