import os

import joblib
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "symptom_service_dataset.csv")
KNN_MODEL_PATH = os.path.join(BASE_DIR, "service_knn.pkl")
SERVICE_DATA_PATH = os.path.join(BASE_DIR, "service_data.pkl")
MODEL_NAME = "all-MiniLM-L6-v2"
REQUIRED_COLUMNS = {"symptoms", "service", "first_aid"}


def train():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    data = pd.read_csv(DATASET_PATH)
    missing_columns = REQUIRED_COLUMNS - set(data.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {', '.join(sorted(missing_columns))}")

    data = data.dropna(subset=["symptoms", "service", "first_aid"]).copy()
    data["symptoms"] = data["symptoms"].astype(str).str.lower().str.strip()
    data["service"] = data["service"].astype(str).str.strip()
    data["first_aid"] = data["first_aid"].astype(str).str.strip()

    if data.empty:
        raise ValueError("Dataset has no usable rows.")

    print(f"Loading SentenceTransformer model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Encoding {len(data)} symptom examples...")
    embeddings = model.encode(data["symptoms"].tolist(), convert_to_numpy=True, show_progress_bar=True)

    print("Training KNN model with cosine similarity...")
    knn = NearestNeighbors(n_neighbors=1, metric="cosine")
    knn.fit(embeddings)

    joblib.dump(knn, KNN_MODEL_PATH)
    joblib.dump(
        {
            "model_name": MODEL_NAME,
            "records": data[["symptoms", "service", "first_aid"]].to_dict("records"),
        },
        SERVICE_DATA_PATH,
    )

    print(f"Saved KNN model: {KNN_MODEL_PATH}")
    print(f"Saved service data: {SERVICE_DATA_PATH}")


if __name__ == "__main__":
    train()
