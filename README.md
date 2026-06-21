# AZAMOV ACADEMY — Ro'yxatdan o'tish Bot

Bu bot foydalanuvchidan: **ism-familiya**, **qiziqish (kurs)**, **telefon raqam** so'raydi,
so'ngra Firebase'dan olingan **majburiy kanallarga obunani tekshiradi**, va obuna bo'lsa
**maxfiy kanal** linkini beradi. Barcha ma'lumotlar **Firebase Firestore**'ga yoziladi.
Admin panel botning o'zi ichida (`/admin` komandasi orqali) ishlaydi.

---

## 1-QADAM: Telegram bot yaratish (BotFather)

1. Telegram'da **@BotFather** ni toping va `/start` bosing.
2. `/newbot` yuboring.
3. Botga nom bering (masalan: `Azamov Academy`).
4. Username bering — `_bot` bilan tugashi kerak (masalan: `azamov_academybot`).
5. BotFather sizga **token** beradi, masalan:
   `7123456789:AAH8x9zL...` — buni saqlab qo'ying, keyin kerak bo'ladi.

## 2-QADAM: O'z Telegram ID'ingizni bilish

1. Telegram'da **@userinfobot** ga yozing.
2. U sizga ID raqamingizni beradi (masalan: `123456789`).
3. Shu raqam — siz admin bo'lasiz.

## 3-QADAM: Firebase loyihasini yaratish

1. https://console.firebase.google.com ga kiring (Google akkaunt bilan).
2. **"Add project" / "Loyiha qo'shish"** bosing, nom bering (masalan: `azamov-academy`).
3. Google Analytics so'ralsa — o'chirib qo'ysangiz ham bo'ladi, kerak emas.
4. Loyiha yaratilgach, chap menyudan **Build → Firestore Database** ga kiring.
5. **"Create database"** bosing, "Start in production mode" tanlang, location tanlang (masalan `eur3`), Enable bosing.

### Service Account kaliti olish (bot Firebase'ga ulanishi uchun)

1. Firebase Console'da yuqori chap burchakdagi ⚙️ **Project settings** ga kiring.
2. **Service accounts** bo'limiga o'ting.
3. **"Generate new private key"** tugmasini bosing → tasdiqlang.
4. `.json` fayl yuklab olinadi (masalan `azamov-academy-firebase-adminsdk-xxxxx.json`).
5. Bu faylni **`serviceAccountKey.json`** deb nomlab, bot fayllari bilan bir papkaga joylashtiring.

   ⚠️ **MUHIM:** Bu fayl maxfiy! Hech kimga yubormang, GitHub'ga ham qo'ymang (public repo bo'lsa).

### Firestore xavfsizlik qoidalari (rules)

Bot **Admin SDK** orqali ulangani uchun (server tomonidan), standart "production mode" qoidalari bot uchun muammo qilmaydi — Admin SDK qoidalarni chetlab o'tadi. Hech narsa o'zgartirish shart emas.

## 4-QADAM: Kompyuterda/serverda botni ishga tushirish

```bash
# 1. Python 3.10+ o'rnatilganini tekshiring
python3 --version

# 2. Loyiha papkasiga kiring
cd azamov_bot

# 3. Virtual environment yarating (tavsiya etiladi)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 4. Kerakli kutubxonalarni o'rnating
pip install -r requirements.txt

# 5. .env faylini yarating
cp .env.example .env
```

`.env` faylini oching va to'ldiring:

```
BOT_TOKEN=BotFather'dan olgan tokeningiz
ADMIN_IDS=123456789
FIREBASE_SERVICE_ACCOUNT=serviceAccountKey.json
```

`serviceAccountKey.json` faylini `azamov_bot` papkasiga qo'ying (bot.py bilan bir joyga).

```bash
# 6. Botni ishga tushiring
python bot.py
```

Terminalda `"Bot ishga tushdi..."` yozuvini ko'rsangiz — tayyor! Telegram'da botingizga `/start` yozing.

---

## 5-QADAM: Botni doimiy ishlatish (server/VPS)

Kompyuteringizni o'chirsangiz, bot ham to'xtaydi. 24/7 ishlashi uchun arzon VPS (masalan Timeweb, Hetzner, yoki any Ubuntu VPS) kerak bo'ladi:

```bash
# Serverda screen yoki systemd orqali fon rejimida ishga tushirish (oddiy yo'l - screen):
sudo apt install screen -y
screen -S azamovbot
cd azamov_bot && source venv/bin/activate && python bot.py
# Chiqish uchun: Ctrl+A keyin D (bot ishlashda davom etadi)
# Qaytib kirish uchun: screen -r azamovbot
```

---

## Admin panel qo'llanmasi

Telegram'da botga `/admin` yozing (faqat `.env` dagi `ADMIN_IDS`da bo'lgan ID'lar uchun ishlaydi):

- **📊 Statistika** — nechta foydalanuvchi, nechtasi to'liq ro'yxatdan o'tgan
- **👥 Foydalanuvchilar** — oxirgi ro'yxatdan o'tganlar (ism, raqam, qiziqish)
- **📢 Majburiy kanallar** — yangi kanal qo'shish yoki o'chirish (cheksiz son)
- **🔐 Maxfiy kanal linkini sozlash** — yopiq kanal havolasini o'rnatish/yangilash

### Majburiy kanal qo'shishda diqqat:

Botni kanalga **admin** qilib qo'shishingiz kerak (obunani tekshira olishi uchun)! Aks holda obuna tekshiruvi xato beradi.

- **Ochiq kanal** uchun: `chat_id` o'rniga `@kanal_username` yozsangiz bo'ladi.
- **Yopiq/maxfiy kanal** uchun: raqamli `chat_id` kerak (masalan `-1001234567890`) — buni bilish uchun kanalga biror xabar yuboring va **@username_to_id_bot** kabi botlar yordamida ID'ni aniqlang, yoki kanal postini forward qilib botga yuboring.

---

## Fayllar tuzilishi

```
azamov_bot/
├── bot.py                  # Asosiy bot logikasi
├── firebase_config.py      # Firebase/Firestore funksiyalari
├── requirements.txt        # Python kutubxonalari
├── .env.example             # Sozlamalar namunasi (.env qiling)
├── serviceAccountKey.json  # Firebase kaliti (o'zingiz qo'shasiz, maxfiy!)
└── README.md
```

## Muammo yuzaga kelsa

- **"BOT_TOKEN .env faylida topilmadi"** → `.env` faylini yaratganingizni va to'g'ri to'ldirganingizni tekshiring.
- **Firebase ulanish xatosi** → `serviceAccountKey.json` fayli to'g'ri papkada ekanini tekshiring.
- **Obuna tekshiruvi ishlamayapti** → botni shu kanalga **admin** qilib qo'shganingizni tekshiring.
