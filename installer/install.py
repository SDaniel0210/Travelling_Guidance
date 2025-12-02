import os
import subprocess
import sys

def create_virtualenv(env_path: str):
    print(f"[INFO] Virtuális környezet létrehozása: {env_path}")
    subprocess.run([sys.executable, "-m", "venv", env_path], check=True)


def install_dependencies(env_path: str):
    print("[INFO] Csomagok telepítése (requirements.txt)...")
    pip_path = (
        os.path.join(env_path, "Scripts", "pip.exe")
        if os.name == "nt"
        else os.path.join(env_path, "bin", "pip")
    )
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    print("[OK] Minden csomag telepítve.")


def activate_message(env_path: str):
    if os.name == "nt":
        activate_cmd = os.path.join(env_path, "Scripts", "activate.bat")
        print("\n[INFO] Aktiváláshoz futtasd ezt parancsot a VSCode terminálban:")
        print(f"{activate_cmd}")
    else:
        activate_cmd = os.path.join(env_path, "bin", "activate")
        print("\n[INFO] Aktiváláshoz futtasd ezt a terminálban:")
        print(f"source {activate_cmd}")

    print("\nEzután indíthatod a programot:")
    print("python main.py")


if __name__ == "__main__":
    print("=== Travel Guidance Telepítő ===")
    env_path = input("Add meg a környezet mappájának nevét (pl. venv): ").strip()

    if not env_path:
        print("[HIBA] Nincs megadva elérési út.")
        sys.exit(1)

    create_virtualenv(env_path)
    install_dependencies(env_path)
    activate_message(env_path)
