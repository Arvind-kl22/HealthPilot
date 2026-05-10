import os
from functools import lru_cache


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
KNN_MODEL_PATH = os.path.join(BASE_DIR, "service_knn.pkl")
SERVICE_DATA_PATH = os.path.join(BASE_DIR, "service_data.pkl")
MODEL_NAME = "all-MiniLM-L6-v2"

EMERGENCY_KEYWORDS = (
    "chest pain",
    "breathing problem",
    "shortness of breath",
    "unconscious",
    "heavy bleeding",
    "stroke",
    "heart attack",
    "severe burn",
    "seizure",
)


class AIServiceError(RuntimeError):
    """Raised when the AI model cannot be loaded or used."""


def normalize_symptoms(symptoms):
    return " ".join(str(symptoms or "").lower().strip().split())


def emergency_result():
    return {
        "service": "Emergency",
        "confidence": 100,
        "first_aid": "Emergency symptoms detected. Visit nearest emergency hospital immediately.",
        "is_emergency": True,
    }


def check_emergency(symptoms):
    normalized = normalize_symptoms(symptoms)
    return any(keyword in normalized for keyword in EMERGENCY_KEYWORDS)


@lru_cache(maxsize=1)
def load_ai_resources():
    if not os.path.exists(KNN_MODEL_PATH) or not os.path.exists(SERVICE_DATA_PATH):
        raise AIServiceError("AI model files not found. Run python train_model.py before using AI prediction.")

    try:
        import joblib
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise AIServiceError("AI dependencies are missing. Run pip install -r requirements.txt.") from exc

    knn = joblib.load(KNN_MODEL_PATH)
    service_data = joblib.load(SERVICE_DATA_PATH)
    records = service_data.get("records") if isinstance(service_data, dict) else service_data
    if not records:
        raise AIServiceError("AI service data is empty. Re-run python train_model.py.")

    model_name = service_data.get("model_name", MODEL_NAME) if isinstance(service_data, dict) else MODEL_NAME
    model = SentenceTransformer(model_name)
    return knn, records, model


def predict_medical_service(symptoms):
    normalized = normalize_symptoms(symptoms)
    if not normalized:
        raise ValueError("Symptoms cannot be empty.")

    if check_emergency(normalized):
        return emergency_result()

    knn, records, model = load_ai_resources()
    symptom_embedding = model.encode([normalized], convert_to_numpy=True)
    distances, indices = knn.kneighbors(symptom_embedding, n_neighbors=1)

    distance = float(distances[0][0])
    record = records[int(indices[0][0])]
    confidence = max(0.0, min(100.0, (1.0 - distance) * 100.0))

    return {
        "service": record["service"],
        "confidence": round(confidence, 2),
        "first_aid": record["first_aid"],
        "is_emergency": record["service"].strip().lower() == "emergency",
    }
