"""
Firebase (Firestore) bilan ishlash uchun yordamchi modul.
Barcha foydalanuvchilar, majburiy kanallar va sozlamalar shu yerda saqlanadi.
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

# --- Firebase ni ishga tushirish ---
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT", "serviceAccountKey.json")

cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Collection nomlari ---
USERS_COLLECTION = "users"
CHANNELS_COLLECTION = "required_channels"


# =========================================================
#                     FOYDALANUVCHILAR
# =========================================================

def get_user(user_id: int):
    """Bitta foydalanuvchini olish."""
    doc = db.collection(USERS_COLLECTION).document(str(user_id)).get()
    return doc.to_dict() if doc.exists else None


def save_user_step(user_id: int, data: dict):
    """Foydalanuvchi ma'lumotini bosqichma-bosqich saqlash/yangilash."""
    ref = db.collection(USERS_COLLECTION).document(str(user_id))
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    ref.set(data, merge=True)


def complete_registration(user_id: int):
    """Ro'yxatdan o'tishni yakunlangan deb belgilash."""
    ref = db.collection(USERS_COLLECTION).document(str(user_id))
    ref.set(
        {
            "registered": True,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        },
        merge=True,
    )


def is_registered(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user.get("registered"))


def get_all_users():
    docs = db.collection(USERS_COLLECTION).stream()
    return [d.to_dict() for d in docs]


def count_users():
    return len(list(db.collection(USERS_COLLECTION).stream()))


def count_registered_users():
    docs = db.collection(USERS_COLLECTION).where("registered", "==", True).stream()
    return len(list(docs))


# =========================================================
#                  MAJBURIY KANALLAR (DINAMIK)
# =========================================================
# Admin panel orqali istalgancha kanal qo'shish/o'chirish mumkin.
# Har bir hujjat: {"chat_id": "@kanal_yoki_-100...", "title": "Kanal nomi", "url": "https://t.me/..."}

def add_required_channel(chat_id: str, title: str, url: str):
    ref = db.collection(CHANNELS_COLLECTION).document(chat_id.replace("@", "").replace("/", "_"))
    ref.set(
        {
            "chat_id": chat_id,
            "title": title,
            "url": url,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def remove_required_channel(doc_id: str):
    db.collection(CHANNELS_COLLECTION).document(doc_id).delete()


def get_required_channels():
    docs = db.collection(CHANNELS_COLLECTION).stream()
    result = []
    for d in docs:
        item = d.to_dict()
        item["doc_id"] = d.id
        result.append(item)
    return result


# =========================================================
#                  MAXFIY KANAL SOZLAMASI
# =========================================================

SETTINGS_DOC = db.collection("settings").document("config")


def set_private_channel_link(link: str):
    SETTINGS_DOC.set({"private_channel_link": link}, merge=True)


def get_private_channel_link():
    doc = SETTINGS_DOC.get()
    if doc.exists:
        return doc.to_dict().get("private_channel_link")
    return None
