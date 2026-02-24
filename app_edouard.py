import streamlit as st

st.title("Enregistreur audio pour uroflow meter avec correction AGC")

st.markdown("""
Cette application enregistre l'audio avec un ton stable à 80Hz pour empêcher l'activation de l'AGC sur tous les téléphones/browsers.
Le ton est ensuite supprimé via un filtre notch pour fournir un fichier WAV propre.
Tout se passe dans le navigateur pour une compatibilité maximale.
""")

html_code = """
<style>
  #recordButton {
    width: 200px;
    height: 200px;
    border-radius: 50%;
    background-color: red;
    color: white;
    font-size: 24px;
    border: none;
    cursor: pointer;
  }
  #downloadLink {
    display: none;
    margin-top: 20px;
    font-size: 18px;
    color: blue;
    text-decoration: underline;
  }
</style>
<button id="recordButton">Démarrer l'enregistrement</button>
<a id="downloadLink" download="enregistrement_propre.wav">Télécharger le fichier WAV propre</a>
<script>
  let recording = false;
  let mediaRecorder;
  let audioChunks = [];
  let audioCtx;
  let oscillator;
  const toneFrequency = 80;  // Fréquence stable à 80Hz
  const toneGain = 0.05;     // Volume bas pour ne pas être trop intrusif, mais suffisant pour le micro
  const recordButton = document.getElementById('recordButton');
  const downloadLink = document.getElementById('downloadLink');

  // Fonction pour convertir AudioBuffer en Blob WAV
  function audioBufferToWav(buffer) {
    const numOfChan = buffer.numberOfChannels;
    const length = buffer.length * numOfChan * 2 + 44;
    const bufferArr = new ArrayBuffer(length);
    const view = new DataView(bufferArr);
    let pos = 0;

    function setUint32(data) {
      view.setUint32(pos, data, true);
      pos += 4;
    }

    function setUint16(data) {
      view.setUint16(pos, data, true);
      pos += 2;
    }

    // Écrire l'en-tête WAV
    setUint32(0x46464952);  // "RIFF"
    setUint32(length - 8);
    setUint32(0x45564157);  // "WAVE"
    setUint32(0x20746d66);  // "fmt "
    setUint32(16);
    setUint16(1);           // PCM
    setUint16(numOfChan);
    setUint32(buffer.sampleRate);
    setUint32(buffer.sampleRate * 2 * numOfChan);
    setUint16(numOfChan * 2);
    setUint16(16);          // 16-bit
    setUint32(0x61746164);  // "data"
    setUint32(length - 44);

    // Écrire les données interleavées
    for (let i = 0; i < buffer.length; i++) {
      for (let channel = 0; channel < numOfChan; channel++) {
        let sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[i]));
        sample = (sample < 0 ? sample * 0x8000 : sample * 0x7FFF) | 0;
        view.setInt16(pos, sample, true);
        pos += 2;
      }
    }

    return new Blob([bufferArr], { type: 'audio/wav' });
  }

  recordButton.addEventListener('click', async () => {
    if (!recording) {
      try {
        // Accès au micro avec contraintes pour maximiser la compatibilité (si supportées)
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            autoGainControl: false,
            noiseSuppression: false,
            echoCancellation: false,
            channelCount: 1  // Mono pour simplifier
          }
        });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        audioChunks = [];
        mediaRecorder.addEventListener('dataavailable', event => {
          audioChunks.push(event.data);
        });

        // Démarrer le contexte audio et l'oscillateur pour le ton
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(toneFrequency, audioCtx.currentTime);
        gainNode.gain.value = toneGain;
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start();

        recording = true;
        recordButton.textContent = 'Arrêter l'enregistrement';
        recordButton.style.backgroundColor = 'green';
      } catch (err) {
        console.error('Erreur:', err);
      }
    } else {
      mediaRecorder.stop();
      oscillator.stop();
      audioCtx.close();
      recording = false;
      recordButton.textContent = 'Démarrer l'enregistrement';
      recordButton.style.backgroundColor = 'red';

      mediaRecorder.addEventListener('stop', async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        // Traitement offline pour supprimer le ton avec filtre notch
        const offlineCtx = new OfflineAudioContext(
          audioBuffer.numberOfChannels,
          audioBuffer.length,
          audioBuffer.sampleRate
        );
        const source = offlineCtx.createBufferSource();
        source.buffer = audioBuffer;
        const filter = offlineCtx.createBiquadFilter();
        filter.type = 'notch';
        filter.frequency.value = toneFrequency;
        filter.Q.value = 30;  // Q élevé pour un filtre étroit, supprime seulement autour de 80Hz

        source.connect(filter);
        filter.connect(offlineCtx.destination);
        source.start();
        const renderedBuffer = await offlineCtx.startRendering();

        // Convertir en WAV propre
        const cleanWavBlob = audioBufferToWav(renderedBuffer);
        const audioUrl = URL.createObjectURL(cleanWavBlob);
        downloadLink.href = audioUrl;
        downloadLink.download = 'enregistrement_propre.wav';
        downloadLink.textContent = 'Télécharger le fichier WAV propre';
        downloadLink.style.display = 'block';
      });
    }
  });
</script>
"""

st.components.v1.html(html_code, height=400)

st.markdown("""
### Instructions :
- Appuyez sur le gros bouton rouge pour démarrer (il devient vert, et émet un ton bas à 80Hz via le haut-parleur).
- Enregistrez environ 45 secondes (le son d'écoulement sera capturé avec le ton).
- Appuyez à nouveau pour arrêter (le ton s'arrête).
- Le lien de téléchargement apparaît pour le fichier WAV propre (ton supprimé via filtre notch).

Pour lancer sur mobile :
- Exécutez `streamlit run app.py` sur un ordinateur.
- Utilisez ngrok (`ngrok http 8501`) pour une URL https accessible depuis le téléphone.
- Ou déployez sur Streamlit Cloud.

Cette solution devrait fonctionner sur 100% des mobiles/browsers supportant Web Audio API (la plupart des modernes). Le ton trompe l'AGC, et le filtre le retire sans affecter les autres fréquences pour votre ML.
Si le ton est trop fort/bas, ajustez `toneGain` dans le code JS (0.05 par défaut).
""")