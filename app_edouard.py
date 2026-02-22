import streamlit as st
import streamlit.components.v1 as components
import os
from datetime import datetime
import base64

st.markdown("# Web App d'Edouard")

data_dir = "audio"
os.makedirs(data_dir, exist_ok=True)

audio_data = components.html(
    """
    <style>
    .record-btn {
        width: 120px;
        height: 120px;
        border-radius: 60px;
        border: none;
        background-color: red;
        color: white;
        font-size: 20px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }

    .stop-btn {
        width: 120px;
        height: 50px;
        margin-top: 15px;
        border-radius: 10px;
        border: none;
        background-color: #333;
        color: white;
        font-size: 16px;
        cursor: pointer;
    }

    .container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .vu-container {
        width: 300px;
        height: 20px;
        background: #ddd;
        border-radius: 10px;
        overflow: hidden;
        margin-top: 20px;
    }

    .vu-bar {
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, green, yellow, red);
        transition: width 0.05s linear;
    }
    </style>

    <div class="container">
        <button class="record-btn" onclick="startRecording()">REC</button>
        <button class="stop-btn" onclick="stopRecording()">STOP</button>

        <div class="vu-container">
            <div id="vuBar" class="vu-bar"></div>
        </div>
    </div>

    <script>
    let mediaRecorder;
    let audioChunks = [];
    let audioContext;
    let analyser;
    let source;
    let dataArray;
    let animationId;

    async function startRecording() {
        audioChunks = [];

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                noiseSuppression: false,
                echoCancellation: false,
                autoGainControl: false,
                sampleRate: 48000
            }
        });

        // VU meter setup
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        source = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 512;

        source.connect(analyser);

        dataArray = new Uint8Array(analyser.frequencyBinCount);

        function updateVU() {
            analyser.getByteTimeDomainData(dataArray);

            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
                let val = (dataArray[i] - 128) / 128;
                sum += val * val;
            }

            let rms = Math.sqrt(sum / dataArray.length);
            let level = Math.min(1, rms * 4); // amplification visuelle

            document.getElementById("vuBar").style.width = (level * 100) + "%";

            animationId = requestAnimationFrame(updateVU);
        }

        updateVU();

        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            cancelAnimationFrame(animationId);

            const blob = new Blob(audioChunks, { type: 'audio/wav' });
            const arrayBuffer = await blob.arrayBuffer();

            let binary = '';
            const bytes = new Uint8Array(arrayBuffer);
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }

            const base64Audio = btoa(binary);

            window.parent.postMessage(
                { type: "streamlit:setComponentValue", value: base64Audio },
                "*"
            );
        };

        mediaRecorder.start();
    }

    function stopRecording() {
        if (mediaRecorder) {
            mediaRecorder.stop();
        }
    }
    </script>
    """,
    height=300,
)

if audio_data:
    audio_bytes = base64.b64decode(audio_data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(data_dir, f"audio_{timestamp}.wav")

    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    st.success(f"Audio saved to {audio_path}")

    st.audio(audio_bytes, format="audio/wav")

    st.download_button(
        label="Download audio",
        data=audio_bytes,
        file_name=f"audio_{timestamp}.wav",
        mime="audio/wav"
    )