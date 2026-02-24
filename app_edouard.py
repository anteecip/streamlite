# app.py
import streamlit as st
import io
import numpy as np
from scipy import signal
import soundfile as sf
from audiorecorder import audiorecorder  # import du composant installé via git

st.set_page_config(page_title="Uroflow Enregistreur - Anti-AGC avec ton 80 Hz", layout="centered")

st.title("Enregistreur uroflow meter (~45 secondes)")

st.markdown("""
**Principe anti-AGC** :  
Pendant tout l'enregistrement, un **ton continu à 80 Hz** (très bas volume) est émis par le haut-parleur du téléphone.  
Cela empêche la plupart des AGC / filtres vocaux de s'activer (car le signal n'est plus "silencieux").  
Le ton est ensuite **supprimé automatiquement** côté serveur via filtre notch avant le téléchargement.

**Instructions** :
1. Clique sur "Démarrer le ton 80 Hz" (émis immédiatement).
2. Puis clique sur le bouton rouge du recorder pour enregistrer.
3. Arrête l'enregistrement → le fichier propre (.wav sans le ton) apparaît pour téléchargement.
""")

# Session state pour contrôler le ton
if 'tone_running' not in st.session_state:
    st.session_state.tone_running = False

# Bouton pour démarrer/arrêter le ton 80 Hz
col1, col2 = st.columns(2)
with col1:
    if st.button("Démarrer le ton 80 Hz (anti-AGC)"):
        st.session_state.tone_running = True
        st.success("Ton démarré – commence l'enregistrement maintenant !")

with col2:
    if st.button("Arrêter le ton"):
        st.session_state.tone_running = False
        st.info("Ton arrêté.")

# Injection JS pour le ton (exécuté client-side)
if st.session_state.tone_running:
    st.components.v1.html(
        """
        <script>
        if (!window.audioCtx || window.audioCtx.state === 'closed') {
            window.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            window.oscillator = window.audioCtx.createOscillator();
            window.gainNode = window.audioCtx.createGain();
            window.oscillator.type = 'sine';
            window.oscillator.frequency.setValueAtTime(80, window.audioCtx.currentTime);
            window.gainNode.gain.value = 0.04;  // Très faible volume – audible mais discret
            window.oscillator.connect(window.gainNode);
            window.gainNode.connect(window.audioCtx.destination);
            window.oscillator.start();
            console.log('Ton 80 Hz démarré');
        }
        </script>
        """,
        height=0
    )
else:
    # Arrêt du ton si demandé
    st.components.v1.html(
        """
        <script>
        if (window.oscillator) {
            window.oscillator.stop();
            window.oscillator = null;
            console.log('Ton 80 Hz arrêté');
        }
        </script>
        """,
        height=0
    )

# Widget d'enregistrement – le composant principal
st.markdown("**Enregistre maintenant (le ton est actif si lancé ci-dessus)**")
audio = audiorecorder(
    "Démarrer l'enregistrement",
    "Arrêter l'enregistrement",
    pause_text="Pause (optionnel)",
    show_visualizer=True,
    sample_rate=44100  # Bonne qualité pour analyse
)

if len(audio) > 0:
    st.success("Enregistrement reçu ! Traitement en cours...")

    # Lecture brute pour vérification (tu entendras le ton dedans)
    st.audio(audio.export().read(), format="audio/wav")

    try:
        # Conversion en numpy + samplerate
        with io.BytesIO(audio.export().read()) as f:
            data, sr = sf.read(f)

        # Suppression du ton 80 Hz via filtre notch (zéro-phase pour éviter distorsion)
        freq_notch = 80.0
        quality_factor = 35.0  # Plus élevé = plus étroit → moins d'impact sur les fréquences utiles
        b, a = signal.iirnotch(freq_notch / (sr / 2.0), quality_factor)
        data_clean = signal.filtfilt(b, a, data)  # filtfilt = zéro déphasage

        # Sauvegarde propre
        buffer = io.BytesIO()
        sf.write(buffer, data_clean, sr, format='WAV', subtype='PCM_16')
        buffer.seek(0)

        st.download_button(
            label="Télécharger WAV propre (sans ton 80 Hz)",
            data=buffer,
            file_name="uroflow_clean.wav",
            mime="audio/wav",
            key="download_clean"
        )

        st.info("Fichier nettoyé ! Le ton a été supprimé via filtre notch.")

    except Exception as e:
        st.error(f"Erreur pendant le traitement : {e}")
        st.info("Essaie un enregistrement plus court (10-20 s) pour tester.")

else:
    st.info("Clique sur le bouton rouge ci-dessus pour enregistrer.")

st.markdown("---")
st.caption("Composant audio : streamlit-audio-recorder (stefanrmmr)")
st.caption("Ton 80 Hz émis client-side via Web Audio API – supprimé serveur-side")
st.caption("Teste d'abord localement puis sur Streamlit Cloud (HTTPS obligatoire)")