import streamlit as st
import io
from scipy import signal
import soundfile as sf

st.title("Enregistreur audio pour uroflow meter avec correction AGC")

st.markdown("""
Cette application utilise les fonctions natives de Streamlit pour l'enregistrement audio.
Pour une compatibilité maximale sur tous les téléphones et navigateurs :
- Utilisez le bouton pour démarrer/arrêter le ton (80Hz) émis via le haut-parleur pour tromper l'AGC.
- Enregistrez ensuite l'audio avec le widget natif.
- Le fichier est traité sur le serveur Streamlit (Python) pour supprimer le ton via un filtre notch.
- Téléchargez le fichier WAV propre.

Note : Le ton est émis client-side via Web Audio API, ce qui fonctionne sur la plupart des mobiles modernes.
""")

# Gestion du ton (80Hz)
if 'tone_active' not in st.session_state:
    st.session_state.tone_active = False

if st.button("Démarrer le ton (80Hz) pour empêcher l'AGC"):
    st.session_state.tone_active = True

if st.session_state.tone_active:
    # JS pour émettre le ton (exécuté client-side)
    st.components.v1.html("""
    <style>
      /* Pour éviter les problèmes de tap highlight sur mobile */
      body { -webkit-tap-highlight-color: transparent; }
    </style>
    <script>
      // Création du contexte audio et oscillateur
      window.audioCtx = window.audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      window.oscillator = window.audioCtx.createOscillator();
      window.gainNode = window.audioCtx.createGain();
      window.oscillator.type = 'sine';
      window.oscillator.frequency.setValueAtTime(80, window.audioCtx.currentTime);
      window.gainNode.gain.value = 0.05;  // Volume bas
      window.oscillator.connect(window.gainNode);
      window.gainNode.connect(window.audioCtx.destination);
      window.oscillator.start();
      console.log('Ton démarré');
    </script>
    """, height=0)

    if st.button("Arrêter le ton"):
        st.session_state.tone_active = False
        # JS pour arrêter le ton
        st.components.v1.html("""
        <script>
          if (window.oscillator) {
            window.oscillator.stop();
            window.oscillator = null;
            console.log('Ton arrêté');
          }
        </script>
        """, height=0)

else:
    # Assurer que le ton est arrêté si state change
    st.components.v1.html("""
    <script>
      if (window.oscillator) {
        window.oscillator.stop();
        window.oscillator = null;
      }
    </script>
    """, height=0)

# Enregistrement audio natif Streamlit
st.markdown("Enregistrez l'audio (environ 45 secondes) pendant que le ton est actif.")
audio = st.audio_input("Appuyez pour démarrer/arrêter l'enregistrement")

if audio:
    st.audio(audio)  # Lecture pour vérification

    # Traitement sur le serveur (Python) pour supprimer le ton à 80Hz
    with io.BytesIO(audio.getvalue()) as audio_io:
        data, sr = sf.read(audio_io)

    # Filtre notch pour supprimer 80Hz
    freq = 80.0
    q = 30.0  # Qualité du filtre (étroit)
    b, a = signal.iirnotch(freq / (sr / 2.0), q)  # Normalisé
    filtered_data = signal.lfilter(b, a, data)  # Utilise lfilter pour causal (ou filtfilt pour non-causal)

    # Écriture du fichier propre en bytes
    buffer = io.BytesIO()
    sf.write(buffer, filtered_data, sr, format='WAV')
    buffer.seek(0)

    # Bouton de téléchargement
    st.download_button(
        label="Télécharger le fichier WAV propre",
        data=buffer,
        file_name="enregistrement_propre.wav",
        mime="audio/wav"
    )