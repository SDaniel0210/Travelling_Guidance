import os
from typing import Optional

from huggingface_hub import InferenceClient


class AIRecommendError(Exception):
    """Utazási ajánló AI-specifikus hiba."""
    pass


HF_DYNAMIC_TOKEN: Optional[str] = None


def set_hf_token(token: str) -> None:
    """GUI-ból beállított HF token (csak memóriában)."""
    global HF_DYNAMIC_TOKEN
    HF_DYNAMIC_TOKEN = token.strip()


def clear_hf_token() -> None:
    global HF_DYNAMIC_TOKEN
    HF_DYNAMIC_TOKEN = None


def _get_hf_client() -> InferenceClient:
    """
    InferenceClient:
    - ha van GUI-ból beállított token → azt használja
    - különben HF_API_TOKEN környezeti változót
    """
    if HF_DYNAMIC_TOKEN:
        token = HF_DYNAMIC_TOKEN
    else:
        token = os.getenv("HF_API_TOKEN")

    if not token:
        raise AIRecommendError(
            "Nincs HuggingFace API token megadva.\n"
            "Beállítások menüben add meg, vagy állítsd be HF_API_TOKEN környezeti változóként."
        )

    # Itt TUDSZ MODELLT CSERÉLNI ha kell
    # Olyat válassz, ami támogatja a chat / conversational hívást.
    model_id = "meta-llama/Meta-Llama-3-8B-Instruct"

    return InferenceClient(model=model_id, token=token)


def ask_travel_ai(user_request: str) -> str:
    """
    Egyszerű chat-szerű hívás.
    Bemenet: felhasználói kérés.
    Kimenet: a modell teljes válasza szövegként (ezt fogjuk betolni a QTextEdit-be).
    """
    text = (user_request or "").strip()
    if not text:
        raise AIRecommendError("Üres kérést nem küldhetsz az AI-nak.")

    client = _get_hf_client()

    system_msg = (
        "Te egy utazási tanácsadó asszisztens vagy. "
        "A felhasználó leírja, milyen jellegű utazást szeretne "
        "(pl. 'északi ország, látványos drónozásra alkalmas helyekkel, "
        "ne legyen túl hideg'), te pedig 3–5 konkrét úti célt ajánlasz.\n\n"
        "Fontos:\n"
        "- Valós városokat/régiókat mondj.\n"
        "- Ne csak Olaszországot ismételgesd; nézd meg, mire kérdez rá (északi, tengerpart, hegyek, stb.).\n"
        "- Írj rövid leírást mindegyikhez (1–3 mondat), felsorolásban.\n"
    )

    try:
        completion = client.chat_completion(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": text},
            ],
            max_tokens=600,
            temperature=0.7,
            top_p=0.9,
        )
    except Exception as e:
        raise AIRecommendError(f"Hiba a HuggingFace híváskor: {e}") from e

    # új HF InferenceClient.chat_completion válaszstruktúra
    try:
        content = completion.choices[0].message["content"]
    except Exception as e:
        raise AIRecommendError(
            f"Nem sikerült kiolvasni az AI válaszát: {e}\nNyers válasz: {completion}"
        ) from e

    return content.strip()
