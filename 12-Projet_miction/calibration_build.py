# ===========================================================
# Calibration DSP + KNN avec scaling
# ===========================================================

import os
import numpy as np
import joblib
import librosa
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from dsp_functions import bandpass_filter, extract_features, segment_audio

# === PARAMETRES ===
SR = 32000
CALIB_FOLDER = "calibration_sounds"  # dossier WAV calibrés
OUTPUT_MODEL = "uroflow_knn_model.pkl"

# === POIDS DSP (favorise la fréquence) ===
weights = {
    'mfcc': 1.0,
    'centroid': 2.0,
    'rms': 0.3
}

X_embeddings = []
y_flows = []

print("🔵 Construction des embeddings de calibration...")

for file in os.listdir(CALIB_FOLDER):
    if file.endswith(".wav"):
        flow_value = float(file.split("_")[1].replace("mls.wav", ""))
        # ("_")[0] ??
        print(flow_value)
        path = os.path.join(CALIB_FOLDER, file)

        # Chargement audio et filtrage
        y, sr = librosa.load(path, sr=SR)
        y = bandpass_filter(y, 200, 6000, sr)

        # Découpage en segments (optionnel mais utile si bruit non constant)
        segments, _ = segment_audio(y, sr)

        for seg in segments:
            feat = extract_features(seg, sr, weights)
            X_embeddings.append(feat)
            y_flows.append(flow_value)

X_embeddings = np.array(X_embeddings)
y_flows = np.array(y_flows)

# ===========================================================
# Scaling des features DSP
# ===========================================================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_embeddings)

# ===========================================================
# KNN
# ===========================================================


'''On n entraîne pas un modèle prédictif.
On construit un espace métrique de référence.
pas d'ajustement de poids mais crétaion index spatial.
construction d index spatial optimisé (KD-Tree ou Ball-Tree)
fit construit une carte spatiale :
“Si je cherche les voisins de ce point, je sais déjà dans quelle zone chercher
Base de signatures acoustiques étalonnées avec un moteur de recherche physique optimisé”
Pas un modèle ML.Un référentiel acoustique
fit ne sert pas à apprendre.
Il sert à organiser intelligemment ta bibliothèque de sons étalons pour que la comparaison soit fiable, 
rapide et robuste.
fit sert à construire la carte.
kneighbors sert à se repérer dessus.'''
nn = NearestNeighbors(n_neighbors=5, metric='euclidean')
nn.fit(X_scaled)


'''Dans uroflow_knn_model.pkl, il y a seulement :
La liste des vecteurs DSP des sons étalonnés
Les débits associés
Une structure de recherche rapide (KD-tree / Ball-tree) pour trouver les voisins les plus proches.'''
print("💾 Sauvegarde du modèle calibré...")
joblib.dump({
    "nn": nn,
    "y_calib": y_flows,
    "weights": weights,
    "scaler": scaler
}, OUTPUT_MODEL)

print("✅ Calibration terminée avec scaling")
