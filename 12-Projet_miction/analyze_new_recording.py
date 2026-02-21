# analyze_and_plot.py

import joblib
import matplotlib.pyplot as plt
from dsp_functions import analyze_recording

MODEL_PATH = "uroflow_knn_model.pkl"
AUDIO_TEST = "test.wav"

model = joblib.load(MODEL_PATH)

nn = model["nn"]
y_calib = model["y_calib"]
weights = model["weights"]

# Choix : "segment" ou "fine"
results = analyze_recording(
    AUDIO_TEST,
    nn,
    y_calib,
    weights,
    mode="fine",
    fine_step=0.2
)

# ===== Affichage =====

times = []
flows = []
t = 0

for r in results:
    times.append(t)
    flows.append(r["debit"])
    t += r["duree"]

plt.figure(figsize=(10,4))
plt.step(times, flows, where='post')
plt.xlabel("Temps (s)")
plt.ylabel("Débit (ml/s)")
plt.title("Courbe uroflow estimée")
plt.grid(True)
plt.show()

