#!/usr/bin/env python3
"""
inject_firebase_sw.py
─────────────────────
Đọc Firebase credentials từ .env.local rồi:
  1. Ghi vào assets/env/dev_config  (Flutter dotenv — đọc lúc runtime)
  2. Ghi vào assets/env/prod_config (Flutter dotenv — đọc lúc runtime)
  3. Ghi vào web/firebase-messaging-sw.js (Service Worker — chỉ đọc được
     hardcode, không đọc được Flutter assets)

Chạy một lần sau khi điền key vào .env.local:
  python inject_firebase_sw.py

Sau đó build như bình thường:
  flutter build web --release
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_LOCAL      = os.path.join(SCRIPT_DIR, ".env.local")
DEV_CONFIG     = os.path.join(SCRIPT_DIR, "assets", "env", "dev_config")
PROD_CONFIG    = os.path.join(SCRIPT_DIR, "assets", "env", "prod_config")
SW_TEMPLATE    = os.path.join(SCRIPT_DIR, "web", "firebase-messaging-sw.js.template")
SW_OUTPUT      = os.path.join(SCRIPT_DIR, "web", "firebase-messaging-sw.js")
DART_OPTIONS   = os.path.join(SCRIPT_DIR, "lib", "firebase_options.dart")

FIREBASE_KEYS = [
    "FIREBASE_API_KEY",
    "FIREBASE_AUTH_DOMAIN",
    "FIREBASE_PROJECT_ID",
    "FIREBASE_STORAGE_BUCKET",
    "FIREBASE_MESSAGING_SENDER_ID",
    "FIREBASE_APP_ID",
    "FIREBASE_MEASUREMENT_ID",
]

# ── helpers ──────────────────────────────────────────────────────────────────

def load_env(path: str) -> dict[str, str]:
    env: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def validate(env: dict[str, str]) -> None:
    missing = [k for k in FIREBASE_KEYS if not env.get(k)]
    placeholder = [k for k in FIREBASE_KEYS if env.get(k, "").startswith("PASTE_")]
    if missing:
        print(f"[ERROR] Thiếu key trong .env.local: {missing}")
        sys.exit(1)
    if placeholder:
        print(f"[ERROR] Chưa điền key thật vào .env.local: {placeholder}")
        print("  → Mở flutter-app/.env.local và thay PASTE_NEW_API_KEY_HERE bằng key mới.")
        sys.exit(1)


def update_config_file(path: str, env: dict[str, str]) -> None:
    """Đọc file config, cập nhật / thêm các FIREBASE_* key."""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        matched = False
        for key in FIREBASE_KEYS:
            if re.match(rf"^{re.escape(key)}\s*=", line):
                new_lines.append(f"{key}={env[key]}\n")
                updated_keys.add(key)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    # Thêm key chưa có vào cuối file
    for key in FIREBASE_KEYS:
        if key not in updated_keys:
            new_lines.append(f"{key}={env[key]}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"  ✓ Updated  {os.path.relpath(path, SCRIPT_DIR)}")


def inject_sw(env: dict[str, str]) -> None:
    """Điền credentials vào SW template → firebase-messaging-sw.js."""
    if not os.path.exists(SW_TEMPLATE):
        print(f"[WARN] Không tìm thấy template: {SW_TEMPLATE}")
        print("       Bỏ qua bước inject Service Worker.")
        return

    with open(SW_TEMPLATE, encoding="utf-8") as f:
        content = f.read()

    replacements = {
        "YOUR_FIREBASE_API_KEY":            env["FIREBASE_API_KEY"],
        "YOUR_FIREBASE_AUTH_DOMAIN":        env["FIREBASE_AUTH_DOMAIN"],
        "YOUR_FIREBASE_PROJECT_ID":         env["FIREBASE_PROJECT_ID"],
        "YOUR_FIREBASE_STORAGE_BUCKET":     env["FIREBASE_STORAGE_BUCKET"],
        "YOUR_FIREBASE_MESSAGING_SENDER_ID": env["FIREBASE_MESSAGING_SENDER_ID"],
        "YOUR_FIREBASE_APP_ID":             env["FIREBASE_APP_ID"],
        "YOUR_FIREBASE_MEASUREMENT_ID":     env["FIREBASE_MEASUREMENT_ID"],
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    with open(SW_OUTPUT, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Generated {os.path.relpath(SW_OUTPUT, SCRIPT_DIR)}")


def inject_dart(env: dict[str, str]) -> None:
    """Điền credentials vào firebase_options.dart."""
    if not os.path.exists(DART_OPTIONS):
        print(f"[WARN] Không tìm thấy: {DART_OPTIONS}")
        return

    with open(DART_OPTIONS, encoding="utf-8") as f:
        content = f.read()

    replacements = {
        "YOUR_FIREBASE_API_KEY":            env["FIREBASE_API_KEY"],
        "YOUR_FIREBASE_APP_ID":             env["FIREBASE_APP_ID"],
        "YOUR_FIREBASE_MESSAGING_SENDER_ID": env["FIREBASE_MESSAGING_SENDER_ID"],
        "YOUR_FIREBASE_PROJECT_ID":         env["FIREBASE_PROJECT_ID"],
        "YOUR_FIREBASE_AUTH_DOMAIN":        env["FIREBASE_AUTH_DOMAIN"],
        "YOUR_FIREBASE_STORAGE_BUCKET":     env["FIREBASE_STORAGE_BUCKET"],
        "YOUR_FIREBASE_MEASUREMENT_ID":     env["FIREBASE_MEASUREMENT_ID"],
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    with open(DART_OPTIONS, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Updated  {os.path.relpath(DART_OPTIONS, SCRIPT_DIR)}")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not os.path.exists(ENV_LOCAL):
        print(f"[ERROR] Không tìm thấy .env.local")
        print(f"  → Copy từ .env.example rồi điền key: cp .env.local.example .env.local")
        sys.exit(1)

    print("🔑 Đang đọc Firebase credentials từ .env.local …")
    env = load_env(ENV_LOCAL)
    validate(env)

    print("\n📝 Đang inject credentials …")
    update_config_file(DEV_CONFIG, env)
    update_config_file(PROD_CONFIG, env)
    inject_sw(env)
    inject_dart(env)

    print("\n✅ Xong! Các file đã được cập nhật:")
    print("   • assets/env/dev_config      (Flutter runtime config)")
    print("   • assets/env/prod_config     (Flutter runtime config)")
    print("   • web/firebase-messaging-sw.js  (Service Worker)")
    print("   • lib/firebase_options.dart  (Dart Firebase init)")
    print()
    print("⚠️  QUAN TRỌNG: Đừng commit firebase_options.dart và")
    print("   firebase-messaging-sw.js sau khi inject (chúng có key thật).")
    print("   Chỉ commit .env.local.example và *.template .")
    print()
    print("▶  Build tiếp theo:")
    print("   flutter build web --release")


if __name__ == "__main__":
    main()
