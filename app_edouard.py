import streamlit as st
import io
import numpy as np
from scipy import signal
import soundfile as sf
from audiorecorder import audiorecorder

st.set_page_config(page_title="Uroflow Enregistreur - Anti-AGC", layout="centered")

st.title("Enregistreur uroflow meter (~45 secondes)")

st.markdown("""
**Fonctionnement anti-AGC** :  
Un ton continu faible à **80 Hz** est émis par le haut-parleur du téléphone pendant l'enregistrement.  
Cela empêche la plupart des AGC / filtres vocaux automatiques de s'activer sur les téléphones modernes.  

Le ton est ensuite supprimé automatiquement via filtre notch avant téléchargement.

**Étapes** :
1. Clique sur **Démarrer ton 80 Hz**
2. Lance l'enregistrement avec le bouton rouge
3. Arrête → télécharge le fichier nettoyé (.wav)
""")

# Contrôle du ton 80 Hz
if 'tone_active' not in st.session_state:
    st.session_state.tone_active = False

col1, col2 = st.columns(2)
with col1:
    if st.button("Démarrer ton 80 Hz (anti-AGC)", type="primary", use_container_width=True):
        st.session_state.tone_active = True
        st.success("Ton actif – commence l'enregistrement")

with col2:
    if st.button("Arrêter ton", use_container_width=True):
        st.session_state.tone_active = False
        st.info("Ton arrêté")

# JS pour émettre le ton (client-side)
if st.session_state.tone_active:
    st.components.v1.html(
        """
        <script>
        (function startTone() {
            if (window.oscillator) return;
            window.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            window.oscillator = window.audioCtx.createOscillator();
            const gainNode = window.audioCtx.createGain();
            window.oscillator.type = 'sine';
            window.oscillator.frequency.value = 80;
            gainNode.gain.value = 0.035;  // faible volume – ajuste si besoin
            window.oscillator.connect(gainNode);
            gainNode.connect(window.audioCtx.destination);
            window.oscillator.start();
            console.log('Ton 80 Hz démarré');
        })();
        </script>
        """,
        height=0
    )
else:
    st.components.v1.html(
        """
        <script>
        if (window.oscillator) {
            window.oscillator.stop();
            window.oscillator = null;
            console.log('Ton arrêté');
        }
        </script>
        """,
        height=0
    )

# Widget d'enregistrement – fréquence native du téléphone
st.markdown("**Enregistrez l'écoulement d'urine (ton actif si démarré ci-dessus)**")
audio = audiorecorder(
    start_prompt="Démarrer l'enregistrement",
    stop_prompt="Arrêter l'enregistrement",
    pause_prompt="",                    # pas de bouton pause
    show_visualizer=True,
    key="uroflow_recorder"
)

if len(audio) > 0:
    st.success("Enregistrement terminé !")

    # Lecture brute (avec ton audible pour vérif)
    st.audio(audio.export(format="wav").read(), format="audio/wav")

    try:
        wav_bytes = audio.export(format="wav").read()
        with io.BytesIO(wav_bytes) as f:
            data, sr = sf.read(f)

        st.caption(f"Fréquence d'échantillonnage détectée : {sr} Hz (fréquence native du téléphone)")

        # Filtre notch pour supprimer ~80 Hz
        notch_freq = 80.0
        q = 35.0  # filtre étroit
        b, a = signal.iirnotch(notch_freq / (sr / 2.0), q)
        data_clean = signal.filtfilt(b, a, data)

        clean_buffer = io.BytesIO()
        sf.write(clean_buffer, data_clean, sr, format='WAV', subtype='PCM_16')
        clean_buffer.seek(0)

        st.download_button(
            label="Télécharger WAV propre (sans ton 80 Hz)",
            data=clean_buffer,
            file_name="uroflow_enregistrement_clean.wav",
            mime="audio/wav",
            use_container_width=True
        )

        st.info("Fichier nettoyé – prêt pour ton analyse ML.")

    except Exception as e:
        st.error(f"Erreur lors du traitement : {str(e)}")
        st.info("Essaie un enregistrement plus court (10-20 s) pour tester.")

else:
    st.info("Appuie sur le bouton rouge ci-dessus. Autorise le microphone quand demandé.")

st.markdown("---")
st.caption("Composant : streamlit-audiorecorder")
st.caption("Fréquence : native du téléphone (généralement 44100 ou 48000 Hz)")
st.caption("Ton 80 Hz client-side • Filtre scipy serveur-side")
st.caption("HTTPS obligatoire sur mobile (Streamlit Cloud)")