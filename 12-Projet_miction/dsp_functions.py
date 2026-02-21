


# StandardScaler obligatoire

# Test comparatif :

# Ridge

# Lasso

# SVR

# KNN

# Cross-validation 5 folds

# Comparer MAE


# ===========================================================
# Acoustic Uroflowmetry - Pipeline 
# ===========================================================

import numpy as np
import pandas as pd
import librosa
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors # non utilsé au final
from sklearn.neighbors import KNeighborsRegressor

# 🔎 NearestNeighbors (recherche de voisins)

# 🤖 KNeighborsRegressor (modèle supervisé)

from scipy.signal import butter, lfilter
import glob
import os

# -----------------------------------------------------------
# 1️⃣ Filtrage passe-bande
# Permet de se concentrer sur les fréquences pertinentes
# (par ex. 200–6000 Hz pour le jet d'urine)
# -----------------------------------------------------------
def bandpass_filter(y, lowcut=200, highcut=6000, sr=32000, order=4):
    nyq = 0.5 * sr
    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(order, [low, high], btype='band')
    y_filt = signal.filtfilt(b, a, y)
    return y_filt

# -----------------------------------------------------------
# 2️⃣ Extraction des features acoustiques
# MFCC, centroid, bandwidth, rolloff, RMS, ZCR
# Pondération configurable pour privilégier fréquence vs amplitude
# -----------------------------------------------------------
def extract_features(y, sr, weights=None):
    """
    y: signal audio
    sr: sample rate
    weights: dict, pondération des features
             exemple: {'mfcc':1, 'centroid':2, 'rms':0.5}
    """
    if weights is None:
        weights = {'mfcc':1.0, 'centroid':1.0, 'bandwidth':1.0,
                   'rolloff':1.0, 'rms':1.0, 'zcr':1.0}

    # Normalisation pour réduire l'effet d'amplitude absolue
    y = y / np.max(np.abs(y) + 1e-6)

    features = []

    # ----- MFCC -----
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20, n_fft=4096, hop_length=512)
    features.extend(np.mean(mfcc, axis=1) * weights.get('mfcc',1.0))

    # ----- Spectral centroid -----
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    features.append(np.mean(centroid) * weights.get('centroid',1.0))

    # ----- Spectral bandwidth -----
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    features.append(np.mean(bandwidth) * weights.get('bandwidth',1.0))

    # ----- Spectral rolloff -----
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)
    features.append(np.mean(rolloff) * weights.get('rolloff',1.0))

    # ----- RMS -----
    rms = librosa.feature.rms(y=y)
    features.append(np.mean(rms) * weights.get('rms',1.0))

    # ----- Zero Crossing Rate (ZCR) -----
    zcr = librosa.feature.zero_crossing_rate(y)
    features.append(np.mean(zcr) * weights.get('zcr',1.0))

    return np.array(features)

# -----------------------------------------------------------
# 3️⃣ Segmentation RMS pour découper le signal en phases
# Détecte les segments de flux actif vs pause
# -----------------------------------------------------------
def segment_audio(y, sr, frame_duration=0.2, threshold=0.01):
    frame_length = int(frame_duration * sr)
    hop_length = frame_length

    rms = librosa.feature.rms(y=y, frame_length=frame_length,
                              hop_length=hop_length)[0]

    segments = []
    start = None

    for i, val in enumerate(rms):
        if val > threshold and start is None:
            start = i
        elif val <= threshold and start is not None:
            segments.append((start, i))
            start = None

    if start is not None:
        segments.append((start, len(rms)))

    return segments, frame_length, frame_duration


# -----------------------------------------------------------
# 4️⃣ Création du dataset de calibration
# Fichiers WAV avec nom contenant le débit (ex: flow_15.0.wav)
# -----------------------------------------------------------
def build_calibration_dataset(folder='calibration', weights=None):
    rows = []

    for file in glob.glob(os.path.join(folder, '*.wav')):
        # Extraire le débit du nom de fichier
        debit = float(os.path.basename(file).split('_')[-1].replace('.wav',''))
        y, sr = librosa.load(file, sr=32000)
        y = bandpass_filter(y, 200, 6000, sr)  # filtrage passe-bande
        feat = extract_features(y, sr, weights)
        rows.append(np.append(feat, debit))

    df = pd.DataFrame(rows)
    df.to_csv('calibration_features.csv', index=False)
    print('Calibration dataset saved.')
    return df

# -----------------------------------------------------------
# 5️⃣ Charger KNN pour recherche de similarité (régression)
# -----------------------------------------------------------
def load_knn_model(csv_path='calibration_features.csv', k=3):
    calib = pd.read_csv(csv_path)
    
    # X = features
    X_calib = calib.iloc[:, :-1].values
    
    # y = débit (target)
    y_calib = calib.iloc[:, -1].values

    # Modèle supervisé
    model = KNeighborsRegressor(
        n_neighbors=k,
        metric='euclidean',
        weights='uniform'   # ou 'distance' si tu veux pondérer par proximité
    )
    
    model.fit(X_calib, y_calib)

    return model

# -----------------------------------------------------------
# 6️⃣ Estimation du débit pour un segment donné
# -----------------------------------------------------------
def estimate_flow(feat, model):
    """
    feat : vecteur features 1D (35 features par ex.)
    model : modèle KNeighborsRegressor déjà entraîné
    """
    
    feat = np.array(feat).reshape(1, -1)  # nécessaire pour sklearn
    prediction = model.predict(feat)

    return prediction[0]

# -----------------------------------------------------------
# 7️⃣ Analyse complète d'une miction avec mode segment ou fine_step
# -----------------------------------------------------------
def analyze_recording(file_path, nn, y_calib,
                      weights=None,
                      scaler=None,  # <--- nouveau paramètre obligatoire pour le scaling
                      mode="segment",
                      measure_step=0.2,
                      frame_duration=0.2):

    y, sr = librosa.load(file_path, sr=32000)
    y = bandpass_filter(y, 200, 6000, sr)

    segments, frame_len, seg_step = segment_audio(y, sr, frame_duration)

    results = []
    global_time = 0
    measure_id = 1

    for phase_id, (s, e) in enumerate(segments, start=1):

        seg = y[s*frame_len:e*frame_len]
        seg_duration = (e - s) * seg_step

        # ================= OPTION 1 =================
        if mode == "segment":
            mid = len(seg)//2
            window = seg[mid - frame_len//2: mid + frame_len//2]

            feat = extract_features(window, sr, weights)
            feat = scaler.transform([feat])[0]  # <--- scaling appliqué ici
            debit = estimate_flow(feat, nn, y_calib)

            results.append({
                "phase": phase_id,
                "debit": debit,
                "duree": seg_duration
            })

        # ================= OPTION 2 =================
        elif mode == "fine":
            step_samples = int(measure_step * sr)

            for start in range(0, len(seg) - step_samples, step_samples):
                window = seg[start:start + step_samples]

                feat = extract_features(window, sr, weights)
                feat = scaler.transform([feat])[0]  # <--- scaling appliqué ici
                debit = estimate_flow(feat, nn, y_calib)

                results.append({
                    "phase": measure_id,  # numéro temporel
                    "debit": debit,
                    "duree": measure_step
                })

                measure_id += 1

    return results


# -----------------------------------------------------------
# 8️⃣ Tracer la courbe débit(t)
# -----------------------------------------------------------
def plot_uroflow(results):
    times = []
    flows = []
    t = 0

    for r in results:
        times.append(t)
        flows.append(r['debit'])
        t += r['duree']

    plt.figure(figsize=(8,4))
    plt.step(times, flows, where='post')
    plt.xlabel('Temps (s)')
    plt.ylabel('Débit (ml/s)')
    plt.title('Courbe de débit estimé (Uroflow)')
    plt.grid(True)
    plt.show()
