import argparse
import os
from cryptography.fernet import Fernet
from pathlib import Path

DEFAULT_ENV = ".env"

def generate_key() -> str:
    return Fernet.generate_key().decode()

def write_to_env(key: str, env_path: str = DEFAULT_ENV) -> None:
    p = Path(env_path)
    lines = []
    if p.exists():
        lines = p.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("FERNET_KEY="):
            new_lines.append(f"FERNET_KEY={key}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and new_lines[-1] != "":
            new_lines.append("")
        new_lines.append(f"FERNET_KEY={key}")
    p.write_text("\n".join(new_lines) + "\n")
    print(f"[+] Written FERNET_KEY to {env_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate a Fernet key and optionally write it to a .env file.")
    parser.add_argument("--write", action="store_true", help="Write key into .env (or file provided by --env-path).")
    parser.add_argument("--env-path", default=DEFAULT_ENV, help="Path to .env file to write (default: .env).")
    parser.add_argument("--show-only", action="store_true", help="Only print the key (same as no flags).")
    args = parser.parse_args()

    key = generate_key()
    print("Generated Fernet key:")
    print(key)
    print()
    if args.write:
        write_to_env(key, args.env_path)
        abs_path = Path(args.env_path).resolve()
        print(f"[!] Güvenlik uyarısı: {abs_path} dosyasını versiyon kontrolüne (git) commit etmeyin.")
    else:
        print("Run with --write to insert/update the key in a .env file.")
        print("Example: python generate_fernet_key.py --write --env-path .env")

if __name__ == "__main__":
    main()
