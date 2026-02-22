import streamlit as st
import streamlit.components.v1 as components
import os
from datetime import datetime
import base64

st.title("Uroflow acoustique - Enregistrement brut")

data_dir = "audio"
os.makedirs(data_dir, exist_ok=True)

audio_base64 = components.html(
"""
<script src="https://unpkg.com/streamlit-component-lib@1.4.0/dist/index.js"></script>

<style>
.record{
width:140px;
height:140px;
border-radius:70px;
background:red;
color:white;
font-size:24px;
border:none;
}

.stop{
width:140px;
height:50px;
margin-top:10px;
}

#timer{
font-size:22px;
margin-top:10px;
}
</style>

<button class="record" onclick="startRec()">REC</button>
<button class="stop" onclick="stopRec()">STOP</button>
<div id="timer">00:00</div>

<script>
let stream;
let audioCtx;
let source;
let processor;
let chunks=[];
let timerInterval;
let seconds=0;

function updateTimer(){
seconds++;
let m=String(Math.floor(seconds/60)).padStart(2,"0");
let s=String(seconds%60).padStart(2,"0");
document.getElementById("timer").innerText=m+":"+s;
}

async function startRec(){

seconds=0;
chunks=[];
document.getElementById("timer").innerText="00:00";
timerInterval=setInterval(updateTimer,1000);

stream = await navigator.mediaDevices.getUserMedia({
audio:{
channelCount:1,
noiseSuppression:false,
echoCancellation:false,
autoGainControl:false
}
});

audioCtx = new (window.AudioContext || window.webkitAudioContext)({sampleRate:48000});
source = audioCtx.createMediaStreamSource(stream);
processor = audioCtx.createScriptProcessor(4096,1,1);

source.connect(processor);
processor.connect(audioCtx.destination);

processor.onaudioprocess = e=>{
chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
};
}

function stopRec(){

clearInterval(timerInterval);

let length=0;
chunks.forEach(c=>length+=c.length);

let data=new Float32Array(length);
let offset=0;

chunks.forEach(c=>{
data.set(c,offset);
offset+=c.length;
});

let wav = encodeWAV(data, audioCtx.sampleRate);
let base64 = arrayBufferToBase64(wav);

// envoi vers Streamlit
window.parent.postMessage({
isStreamlitMessage: true,
type: "streamlit:setComponentValue",
value: base64
}, "*");

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
height=260,
)

# correction importante ici
if isinstance(audio_base64, str) and len(audio_base64) > 100:
    try:
        audio_bytes = base64.b64decode(audio_base64)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(data_dir, f"audio_{timestamp}.wav")

        with open(path, "wb") as f:
            f.write(audio_bytes)

        st.success("Audio reçu")

        st.audio(audio_bytes)

        st.download_button(
            "Télécharger",
            audio_bytes,
            file_name=f"audio_{timestamp}.wav",
            mime="audio/wav"
        )

    except Exception as e:
        st.error(f"Erreur décodage audio: {e}")