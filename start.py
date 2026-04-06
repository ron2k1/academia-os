"""AcademiaOS startup script — starts server connected to OpenClaw gateway."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _check(label: str, ok: bool, detail: str = "") -> None:
    """Print a status line."""
    mark = "OK" if ok else "!!"
    line = f"  [{mark}] {label}"
    if detail:
        line += f"  ({detail})"
    print(line)


def _wait_for_http(url: str, token: str = "", timeout: int = 10) -> bool:
    """Poll an HTTP endpoint until it responds 200 or timeout."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> None:
    """Start AcademiaOS connected to OpenClaw."""
    # Load .env
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    print()
    print("=" * 42)
    print("         AcademiaOS Starting")
    print("    OpenClaw Academic Workspace")
    print("=" * 42)
    print()

    # --- Pre-flight checks ---
    print("Pre-flight checks:")

    # 1. Config
    classes_json = ROOT / "config" / "classes.json"
    _check("config/classes.json", classes_json.exists())
    if not classes_json.exists():
        print("  ERROR: Copy config/classes.example.json to config/classes.json first.")
        sys.exit(1)

    # 2. Claude CLI
    claude = shutil.which("claude") or shutil.which("claude.cmd")
    _check("Claude CLI", bool(claude), claude or "not found")
    if not claude:
        print("  ERROR: Claude CLI not found. Install from https://claude.ai/code")
        sys.exit(1)

    # 3. OpenClaw gateway
    oc_http = os.environ.get("OPENCLAW_GATEWAY_HTTP", "http://localhost:18789")
    oc_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
    oc_alive = _wait_for_http(f"{oc_http}/health", token=oc_token, timeout=3)
    _check("OpenClaw gateway", oc_alive, oc_http if oc_alive else "not reachable — start with: openclaw gateway run")

    # 4. OpenRouter key
    or_key = os.environ.get("OPENROUTER_API_KEY", "")
    _check("OpenRouter API key", bool(or_key), "configured" if or_key else "missing from .env")

    print()

    # --- Scaffold vaults ---
    vaults_dir = ROOT / "vaults"
    if not any(vaults_dir.iterdir()) if vaults_dir.exists() else True:
        print("Scaffolding class directories...")
        subprocess.run(
            [sys.executable, "scripts/init_semester.py",
             "--config", str(classes_json), "--root", str(ROOT)],
            cwd=ROOT, check=False
        )

    # --- Start AcademiaOS server ---
    port = int(os.environ.get("GATEWAY_PORT", "8100"))
    print(f"Starting AcademiaOS gateway on port {port}...")

    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.server:app",
         "--host", "0.0.0.0", "--port", str(port), "--log-level", "info"],
        cwd=ROOT,
    )

    # Wait for it to be ready
    if _wait_for_http(f"http://localhost:{port}/health", timeout=15):
        print()
        print("=" * 42)
        print("  AcademiaOS is running!")
        print("")
        print(f"  Frontend:    http://localhost:{port}")
        print(f"  Dashboard:   http://localhost:{port}/dashboard")
        print(f"  Health:      http://localhost:{port}/api/health")
        print(f"  OpenClaw:    {oc_http} ({'connected' if oc_alive else 'offline'})")
        print("=" * 42)
        print()
        print("  Press Ctrl+C to stop.")
        print()
    else:
        print("  WARNING: Server did not respond in time — check logs above.")

    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down AcademiaOS...")
        server_proc.terminate()
        server_proc.wait(timeout=5)
        print("Done.")


if __name__ == "__main__":
    main()
