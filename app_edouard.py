import streamlit as st
import base64

st.set_page_config(
    page_title="Uroflow Recorder",
    page_icon="🎙️",
    layout="centered"
)

st.markdown("""
<style>
    body { background-color: #0e0e0e; color: white; }
    .stApp { background-color: #0e0e0e; }

    #record-btn {
        width: 200px;
        height: 200px;
        border-radius: 50%;
        font-size: 1.4rem;
        font-weight: bold;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 0 30px rgba(220,50,50,0.6);
        display: block;
        margin: 20px auto;
    }
    #record-btn.idle {
        background: radial-gradient(circle, #ff4444, #aa0000);
        color: white;
    }
    #record-btn.recording {
        background: radial-gradient(circle, #ff9900, #cc6600);
        color: white;
        animation: pulse 1s infinite;
        box-shadow: 0 0 50px rgba(255,150,0,0.8);
    }
    @keyframes pulse {
        0%   { transform: scale(1); }
        50%  { transform: scale(1.07); }
        100% { transform: scale(1); }
    }

    #status {
        text-align: center;
        font-size: 1.1rem;
        color: #aaaaaa;
        margin: 10px 0 20px;
    }
    #timer {
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        color: #ff9900;
        min-height: 3rem;
    }
    #download-section {
        text-align: center;
        margin-top: 30px;
        display: none;
    }
    #download-btn {
        background: #1a8a1a;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 16px 40px;
        font-size: 1.2rem;
        cursor: pointer;
        box-shadow: 0 0 20px rgba(0,200,0,0.4);
    }
    #download-btn:hover { background: #22aa22; }

    #warning {
        background: #1a1a00;
        border: 1px solid #ffcc00;
        border-radius: 8px;
        padding: 10px 16px;
        color: #ffcc00;
        font-size: 0.85rem;
        margin: 10px auto;
        max-width: 400px;
        text-align: center;
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;color:white;'>🎙️ Uroflow Meter</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#888;'>Enregistrement audio — durée cible : ~45 secondes</p>", unsafe_allow_html=True)

st.markdown("""
<div id="warning">⚠️ Enregistrement arrêté automatiquement après 60s</div>
<div id="timer"></div>
<button id="record-btn" class="idle" onclick="toggleRecording()">⏺ ENREGISTRER</button>
<div id="status">Appuyez pour démarrer</div>
<div id="download-section">
    <p style="color:#aaa;">Enregistrement prêt :</p>
    <a id="download-link" download="uroflow.wav">
        <button id="download-btn">⬇️ Télécharger .WAV</button>
    </a>
</div>

<script>
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let timerInterval = null;
let seconds = 0;
let audioContext = null;
let sourceNode = null;
let destinationNode = null;

function formatTime(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
}

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        stopRecording();
    }
}

async function startRecording() {
    try {
        // Désactivation explicite AGC / noise suppression / echo cancellation
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
                sampleRate: 44100,
                channelCount: 1
            }
        });

        // On utilise AudioContext pour capturer le PCM brut et encoder en WAV
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
        sourceNode = audioContext.createMediaStreamSource(stream);

        // ScriptProcessor pour récupérer les samples PCM bruts
        const bufferSize = 4096;
        const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
        
        let pcmData = [];
        
        processor.onaudioprocess = function(e) {
            if (!isRecording) return;
            const inputData = e.inputBuffer.getChannelData(0);
            pcmData.push(new Float32Array(inputData));
        };

        sourceNode.connect(processor);
        processor.connect(audioContext.destination);

        isRecording = true;
        seconds = 0;
        audioChunks = pcmData; // référence partagée

        const btn = document.getElementById('record-btn');
        btn.className = 'recording';
        btn.textContent = '⏹ STOP';
        document.getElementById('status').textContent = 'Enregistrement en cours...';
        document.getElementById('download-section').style.display = 'none';
        document.getElementById('timer').textContent = formatTime(0);
        document.getElementById('warning').style.display = 'none';

        timerInterval = setInterval(() => {
            seconds++;
            document.getElementById('timer').textContent = formatTime(seconds);
            if (seconds >= 60) {
                document.getElementById('warning').style.display = 'block';
                stopRecording();
            }
        }, 1000);

        // Stocker références pour stop
        window._processor = processor;
        window._stream = stream;
        window._pcmData = pcmData;

    } catch (err) {
        document.getElementById('status').textContent = '❌ Erreur micro : ' + err.message;
    }
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    clearInterval(timerInterval);

    const btn = document.getElementById('record-btn');
    btn.className = 'idle';
    btn.textContent = '⏺ ENREGISTRER';
    document.getElementById('status').textContent = 'Traitement...';

    // Arrêt propre
    if (window._processor) window._processor.disconnect();
    if (window._stream) window._stream.getTracks().forEach(t => t.stop());

    setTimeout(() => {
        const pcmData = window._pcmData || [];
        if (pcmData.length === 0) {
            document.getElementById('status').textContent = 'Aucune donnée enregistrée.';
            return;
        }

        // Encodage WAV depuis Float32 PCM
        const wavBlob = encodeWAV(pcmData, 44100);
        const url = URL.createObjectURL(wavBlob);
        
        document.getElementById('download-link').href = url;
        document.getElementById('download-section').style.display = 'block';
        document.getElementById('status').textContent = `✅ ${formatTime(seconds)} enregistrés`;
        document.getElementById('timer').textContent = formatTime(seconds);
    }, 200);
}

function encodeWAV(pcmChunks, sampleRate) {
    // Fusionner tous les chunks Float32
    let totalLength = 0;
    pcmChunks.forEach(c => totalLength += c.length);
    const combined = new Float32Array(totalLength);
    let offset = 0;
    pcmChunks.forEach(c => {
        combined.set(c, offset);
        offset += c.length;
    });

    // Convertir Float32 -> Int16
    const int16 = new Int16Array(combined.length);
    for (let i = 0; i < combined.length; i++) {
        let s = Math.max(-1, Math.min(1, combined[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    // Construire le header WAV
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * bitsPerSample / 8;
    const blockAlign = numChannels * bitsPerSample / 8;
    const dataSize = int16.byteLength;
    const bufferSize = 44 + dataSize;

    const buffer = new ArrayBuffer(bufferSize);
    const view = new DataView(buffer);

    function writeString(offset, str) {
        for (let i = 0; i < str.length; i++)
            view.setUint8(offset + i, str.charCodeAt(i));
    }

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);         // chunk size
    view.setUint16(20, 1, true);          // PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);

    const int16Buffer = new Int16Array(buffer, 44);
    int16Buffer.set(int16);

    return new Blob([buffer], { type: 'audio/wav' });
}
</script>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<p style='color:#555;font-size:0.8rem;text-align:center;'>
AGC/NS/EC désactivés via WebAudio API · PCM 16-bit 44.1kHz · WAV natif
</p>
""", unsafe_allow_html=True)