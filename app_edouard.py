import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Uroflow Recorder",
    page_icon="🎙️",
    layout="centered"
)

st.markdown("""
<style>
.stApp { background-color: #0e0e0e; }
h1 { color: white; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>🎙️ Uroflow Meter</h1>", unsafe_allow_html=True)

components.html("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0e0e0e;
    color: white;
    font-family: Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px;
    min-height: 500px;
  }

  #timer {
    font-size: 3rem;
    font-weight: bold;
    color: #ff9900;
    margin: 10px 0;
    min-height: 60px;
  }

  #record-btn {
    width: 180px;
    height: 180px;
    border-radius: 50%;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    font-weight: bold;
    color: white;
    background: radial-gradient(circle, #ff4444, #aa0000);
    box-shadow: 0 0 30px rgba(220,50,50,0.7);
    transition: all 0.3s;
    margin: 20px 0;
    -webkit-tap-highlight-color: transparent;
  }

  #record-btn.recording {
    background: radial-gradient(circle, #ffaa00, #cc6600);
    box-shadow: 0 0 50px rgba(255,150,0,0.9);
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0%   { transform: scale(1); }
    50%  { transform: scale(1.08); }
    100% { transform: scale(1); }
  }

  #status {
    color: #aaa;
    font-size: 1rem;
    text-align: center;
    margin: 8px 0;
    min-height: 24px;
  }

  #warning {
    background: #1a1a00;
    border: 1px solid #ffcc00;
    border-radius: 8px;
    padding: 8px 16px;
    color: #ffcc00;
    font-size: 0.85rem;
    margin: 8px 0;
    display: none;
    text-align: center;
  }

  #download-section {
    display: none;
    flex-direction: column;
    align-items: center;
    margin-top: 20px;
    width: 100%;
  }

  #download-btn {
    background: #1a8a1a;
    color: white;
    border: none;
    border-radius: 12px;
    padding: 18px 40px;
    font-size: 1.2rem;
    cursor: pointer;
    box-shadow: 0 0 20px rgba(0,200,0,0.5);
    width: 80%;
    max-width: 300px;
    -webkit-tap-highlight-color: transparent;
  }
</style>
</head>
<body>

<div id="timer">00:00</div>
<button id="record-btn" onclick="toggleRecording()">&#9210; ENREGISTRER</button>
<div id="status">Appuyez pour démarrer</div>
<div id="warning">⚠️ Arrêt automatique à 60s</div>

<div id="download-section">
  <p style="color:#aaa; margin-bottom:10px;">Enregistrement prêt :</p>
  <a id="dl-link" download="uroflow.wav" style="width:80%;max-width:300px;text-decoration:none;">
    <button id="download-btn">&#11015; Télécharger WAV</button>
  </a>
</div>

<script>
var isRecording = false;
var timerInterval = null;
var seconds = 0;
var audioCtx = null;
var processor = null;
var stream = null;
var pcmChunks = [];

function formatTime(s) {
  var m = Math.floor(s / 60);
  var sec = s % 60;
  return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
}

function toggleRecording() {
  if (!isRecording) {
    startRecording();
  } else {
    stopRecording();
  }
}

function startRecording() {
  var constraints = {
    audio: {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
      sampleRate: { ideal: 44100 },
      channelCount: 1
    }
  };

  navigator.mediaDevices.getUserMedia(constraints)
    .then(function(s) {
      stream = s;
      pcmChunks = [];

      var sampleRate = 44100;
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: sampleRate });
      } catch(e) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }

      var source = audioCtx.createMediaStreamSource(stream);
      processor = audioCtx.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = function(e) {
        if (!isRecording) return;
        var data = e.inputBuffer.getChannelData(0);
        pcmChunks.push(new Float32Array(data));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      isRecording = true;
      seconds = 0;

      var btn = document.getElementById('record-btn');
      btn.className = 'recording';
      btn.textContent = 'STOP';
      document.getElementById('status').textContent = 'Enregistrement en cours...';
      document.getElementById('download-section').style.display = 'none';
      document.getElementById('warning').style.display = 'none';
      document.getElementById('timer').textContent = '00:00';

      timerInterval = setInterval(function() {
        seconds++;
        document.getElementById('timer').textContent = formatTime(seconds);
        if (seconds >= 60) {
          document.getElementById('warning').style.display = 'block';
          stopRecording();
        }
      }, 1000);
    })
    .catch(function(err) {
      document.getElementById('status').textContent = 'Erreur micro : ' + err.message;
      console.error(err);
    });
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;
  clearInterval(timerInterval);

  if (processor) { processor.disconnect(); processor = null; }
  if (stream) { stream.getTracks().forEach(function(t){ t.stop(); }); }

  var btn = document.getElementById('record-btn');
  btn.className = '';
  btn.textContent = 'ENREGISTRER';
  document.getElementById('status').textContent = 'Encodage WAV...';

  var savedSeconds = seconds;

  setTimeout(function() {
    try {
      var sr = audioCtx ? audioCtx.sampleRate : 44100;
      var wav = buildWAV(pcmChunks, sr);
      var url = URL.createObjectURL(wav);
      document.getElementById('dl-link').href = url;
      document.getElementById('download-section').style.display = 'flex';
      document.getElementById('status').textContent = '✅ ' + formatTime(savedSeconds) + ' enregistrés';
    } catch(e) {
      document.getElementById('status').textContent = 'Erreur encodage : ' + e.message;
    }
  }, 300);
}

function buildWAV(chunks, sampleRate) {
  var total = 0;
  for (var i = 0; i < chunks.length; i++) total += chunks[i].length;

  var merged = new Float32Array(total);
  var offset = 0;
  for (var i = 0; i < chunks.length; i++) {
    merged.set(chunks[i], offset);
    offset += chunks[i].length;
  }

  var int16 = new Int16Array(merged.length);
  for (var i = 0; i < merged.length; i++) {
    var s = Math.max(-1, Math.min(1, merged[i]));
    int16[i] = s < 0 ? s * 32768 : s * 32767;
  }

  var numChannels = 1;
  var bitsPerSample = 16;
  var byteRate = sampleRate * numChannels * bitsPerSample / 8;
  var blockAlign = numChannels * bitsPerSample / 8;
  var dataSize = int16.byteLength;

  var buf = new ArrayBuffer(44 + dataSize);
  var view = new DataView(buf);

  function ws(off, str) {
    for (var i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i));
  }

  ws(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  ws(8, 'WAVE');
  ws(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  ws(36, 'data');
  view.setUint32(40, dataSize, true);

  new Int16Array(buf, 44).set(int16);

  return new Blob([buf], { type: 'audio/wav' });
}
</script>

</body>
</html>
""", height=540, scrolling=False)