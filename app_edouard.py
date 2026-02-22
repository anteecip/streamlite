import streamlit as st
import streamlit.components.v1 as components
import os
from datetime import datetime
import base64

st.title("Web App d'Edouard – Enregistrement brut + spectre + timer")

data_dir = "audio"
os.makedirs(data_dir, exist_ok=True)

audio_base64 = components.html(
"""
<style>
.container{
    display:flex;
    flex-direction:column;
    align-items:center;
    font-family:sans-serif;
}

.record-btn{
    width:150px;
    height:150px;
    border-radius:75px;
    background:red;
    color:white;
    font-size:26px;
    border:none;
    margin-top:10px;
}

.stop-btn{
    width:150px;
    height:50px;
    margin-top:10px;
    font-size:18px;
}

#timer{
    margin-top:12px;
    font-size:22px;
    font-weight:bold;
}

canvas{
    margin-top:15px;
    background:black;
}
</style>

<div class="container">
<button class="record-btn" onclick="startRec()">REC</button>
<button class="stop-btn" onclick="stopRec()">STOP</button>
<div id="timer">00:00</div>
<canvas id="spec" width="420" height="160"></canvas>
</div>

<script>
let stream;
let ctxAudio;
let source;
let processor;
let analyser;
let chunks=[];
let timerInterval;
let seconds=0;

const timer=document.getElementById("timer");
const canvas=document.getElementById("spec");
const ctx=canvas.getContext("2d");

function updateTimer(){
    seconds++;
    let m=String(Math.floor(seconds/60)).padStart(2,"0");
    let s=String(seconds%60).padStart(2,"0");
    timer.innerText=m+":"+s;
}

async function startRec(){

    seconds=0;
    timer.innerText="00:00";
    chunks=[];

    timerInterval=setInterval(updateTimer,1000);

    stream = await navigator.mediaDevices.getUserMedia({
        audio:{
            channelCount:1,
            noiseSuppression:false,
            echoCancellation:false,
            autoGainControl:false
        }
    });

    ctxAudio = new (window.AudioContext || window.webkitAudioContext)({sampleRate:48000});
    source = ctxAudio.createMediaStreamSource(stream);

    analyser = ctxAudio.createAnalyser();
    analyser.fftSize = 1024;

    processor = ctxAudio.createScriptProcessor(4096,1,1);

    source.connect(analyser);
    analyser.connect(processor);
    processor.connect(ctxAudio.destination);

    processor.onaudioprocess = e=>{
        chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };

    draw();
}

function draw(){
    const bufferLength=analyser.frequencyBinCount;
    const data=new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(data);

    ctx.fillStyle="black";
    ctx.fillRect(0,0,canvas.width,canvas.height);

    let barWidth=(canvas.width/bufferLength)*2;
    let x=0;

    for(let i=0;i<bufferLength;i++){
        let h=data[i]/2;
        ctx.fillStyle="rgb(0,200,255)";
        ctx.fillRect(x,canvas.height-h,barWidth,h);
        x+=barWidth+1;
    }

    requestAnimationFrame(draw);
}

function stopRec(){

    clearInterval(timerInterval);

    processor.disconnect();
    source.disconnect();

    let length=0;
    chunks.forEach(c=>length+=c.length);

    let data=new Float32Array(length);
    let offset=0;

    chunks.forEach(c=>{
        data.set(c,offset);
        offset+=c.length;
    });

    let wav = encodeWAV(data, ctxAudio.sampleRate);
    let base64 = arrayBufferToBase64(wav);

    // envoi à Streamlit (méthode stable)
    Streamlit.setComponentValue(base64);

    stream.getTracks().forEach(t=>t.stop());
}

function encodeWAV(samples, sampleRate){
    let buffer=new ArrayBuffer(44+samples.length*2);
    let view=new DataView(buffer);

    function writeString(view,offset,string){
        for(let i=0;i<string.length;i++){
            view.setUint8(offset+i,string.charCodeAt(i));
        }
    }

    writeString(view,0,'RIFF');
    view.setUint32(4,36+samples.length*2,true);
    writeString(view,8,'WAVE');

    writeString(view,12,'fmt ');
    view.setUint32(16,16,true);
    view.setUint16(20,1,true);
    view.setUint16(22,1,true);
    view.setUint32(24,sampleRate,true);
    view.setUint32(28,sampleRate*2,true);
    view.setUint16(32,2,true);
    view.setUint16(34,16,true);

    writeString(view,36,'data');
    view.setUint32(40,samples.length*2,true);

    let offset=44;
    for(let i=0;i<samples.length;i++,offset+=2){
        let s=Math.max(-1,Math.min(1,samples[i]));
        view.setInt16(offset,s*0x7fff,true);
    }

    return buffer;
}

function arrayBufferToBase64(buffer){
    let binary='';
    let bytes=new Uint8Array(buffer);
    for(let i=0;i<bytes.byteLength;i++){
        binary+=String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}
</script>
""",
height=520,
)

# réception audio
if audio_base64:
    audio_bytes = base64.b64decode(audio_base64)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(data_dir, f"audio_{timestamp}.wav")

    with open(path,"wb") as f:
        f.write(audio_bytes)

    st.success("Enregistrement terminé")

    st.audio(audio_bytes)

    st.download_button(
        "Télécharger le fichier WAV",
        audio_bytes,
        file_name=f"audio_{timestamp}.wav",
        mime="audio/wav"
    )