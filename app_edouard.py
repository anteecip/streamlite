import streamlit as st
import streamlit.components.v1 as components
import os
from datetime import datetime
import base64

st.markdown("# Web App d'Edouard - Spectre temps réel + Timer")

data_dir = "audio"
os.makedirs(data_dir, exist_ok=True)

audio_data = components.html(
    """
    <style>
    .record-btn { width:130px; height:130px; border-radius:65px; background:red; color:white; font-size:22px; font-weight:bold; cursor:pointer; box-shadow:0 6px 20px rgba(0,0,0,0.3); border:none; }
    .stop-btn { width:130px; height:50px; margin-top:15px; border-radius:10px; border:none; background:#333; color:white; font-size:16px; cursor:pointer; }
    .container { display:flex; flex-direction:column; align-items:center; }
    canvas { margin-top:10px; background:#111; border-radius:5px; }
    #timer { margin-top:10px; color:white; font-size:18px; font-weight:bold; }
    </style>

    <div class="container">
        <button class="record-btn" onclick="startRecording()">REC</button>
        <button class="stop-btn" onclick="stopRecording()">STOP</button>
        <div id="timer">00:00</div>
        <canvas id="spectrum" width="400" height="150"></canvas>
    </div>

    <script>
    let audioContext, processor, input, globalStream, audioData=[], analyser, animationId;
    let seconds = 0, timerInterval;
    const canvas = document.getElementById("spectrum");
    const ctx = canvas.getContext("2d");
    const timerDiv = document.getElementById("timer");

    async function startRecording() {
        audioData = [];
        seconds = 0;
        timerDiv.textContent = "00:00";

        // Timer en direct
        timerInterval = setInterval(() => {
            seconds++;
            let m = String(Math.floor(seconds/60)).padStart(2,"0");
            let s = String(seconds%60).padStart(2,"0");
            timerDiv.textContent = `${m}:${s}`;
        }, 1000);

        // ==== Ici on désactive DSP / AGC ====
        globalStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                noiseSuppression: false,
                echoCancellation: false,
                autoGainControl: false
            }
        });

        audioContext = new (window.AudioContext || window.webkitAudioContext)({sampleRate:48000});
        input = audioContext.createMediaStreamSource(globalStream);
        analyser = audioContext.createAnalyser(); analyser.fftSize=1024;
        processor = audioContext.createScriptProcessor(4096,1,1);

        input.connect(analyser); analyser.connect(processor); processor.connect(audioContext.destination);

        processor.onaudioprocess = function(e) { audioData.push(new Float32Array(e.inputBuffer.getChannelData(0))); }

        function drawSpectrum() {
            const bufferLength=analyser.frequencyBinCount;
            const dataArray=new Uint8Array(bufferLength);
            analyser.getByteFrequencyData(dataArray);

            ctx.fillStyle="#111"; ctx.fillRect(0,0,canvas.width,canvas.height);
            const barWidth=(canvas.width/bufferLength)*2.5; let x=0;
            for(let i=0;i<bufferLength;i++){
                const barHeight=dataArray[i]/2;
                const r=barHeight+50, g=50, b=200;
                ctx.fillStyle=`rgb(${r},${g},${b})`;
                ctx.fillRect(x,canvas.height-barHeight,barWidth,barHeight);
                x+=barWidth+1;
            }
            animationId=requestAnimationFrame(drawSpectrum);
        }
        drawSpectrum();
    }

    function stopRecording() {
        clearInterval(timerInterval); // stop timer
        cancelAnimationFrame(animationId);
        processor.disconnect(); input.disconnect();

        let length=0; audioData.forEach(chunk=>length+=chunk.length);
        let merged=new Float32Array(length), offset=0;
        audioData.forEach(chunk=>{ merged.set(chunk, offset); offset+=chunk.length; });

        let wavBuffer=encodeWAV(merged, audioContext.sampleRate);
        let base64Audio=arrayBufferToBase64(wavBuffer);

        // Envoi du fichier WAV à Streamlit
        window.parent.postMessage({type:"streamlit:setComponentValue", value:base64Audio}, "*");

        globalStream.getTracks().forEach(track=>track.stop());
    }

    function encodeWAV(samples,sampleRate){
        let buffer=new ArrayBuffer(44+samples.length*2); let view=new DataView(buffer);
        function writeString(view, offset, string){for(let i=0;i<string.length;i++){view.setUint8(offset+i,string.charCodeAt(i));}}
        writeString(view,0,'RIFF'); view.setUint32(4,36+samples.length*2,true); writeString(view,8,'WAVE');
        writeString(view,12,'fmt '); view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
        view.setUint32(24,sampleRate,true); view.setUint32(28,sampleRate*2,true); view.setUint16(32,2,true); view.setUint16(34,16,true);
        writeString(view,36,'data'); view.setUint32(40,samples.length*2,true);
        let offset=44; for(let i=0;i<samples.length;i++,offset+=2){let s=Math.max(-1,Math.min(1,samples[i])); view.setInt16(offset,s*0x7fff,true);}
        return buffer;
    }

    function arrayBufferToBase64(buffer){let binary=''; const bytes=new Uint8Array(buffer); for(let i=0;i<bytes.byteLength;i++){binary+=String.fromCharCode(bytes[i]);} return btoa(binary);}
    </script>
    """,
    height=450,
)

# réception et sauvegarde du WAV
if audio_data and isinstance(audio_data, str) and len(audio_data) > 0:
    try:
        audio_bytes = base64.b64decode(audio_data.encode("utf-8"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = os.path.join(data_dir, f"audio_{timestamp}.wav")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        st.success(f"Audio saved to {audio_path}")
        st.audio(audio_bytes)
        st.download_button(
            label="Download audio",
            data=audio_bytes,
            file_name=f"audio_{timestamp}.wav",
            mime="audio/wav"
        )
    except Exception as e:
        st.error(f"Erreur audio: {e}")