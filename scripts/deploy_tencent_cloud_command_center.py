#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Deploy the command-center worktree to Tencent Cloud and restore the real
layered PostgreSQL logistics data.

Secrets are read from the user-provided startup/credential files and are never
printed. The PostgreSQL dump is created in custom format and removed after the
remote restore completes.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import posixpath
import secrets
import shlex
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import paramiko

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
STARTUP_FILE = Path(r"C:\Users\Administrator\Desktop\物流路径规划系统项目启动方式.txt")
CREDS_FILE = Path(r"C:\Users\Administrator\Desktop\腾讯云服务器.txt")
PG_DUMP = Path(r"D:\PostgreSQL\bin\pg_dump.exe")
DEFAULT_HOST = "122.152.220.116"
DEFAULT_USER = "ubuntu"
REMOTE_RELEASE = "/opt/logistics-route-system"

EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".playwright-mcp",
    "__pycache__",
    "node_modules",
    "dist",
    "venv",
    "logs",
    "data",
    "database",
    "instance",
}

EXCLUDE_TOP_LEVEL = {
    "bigdata-templates",
    "dags",
    "flink",
    "spark-apps",
    "memory",
    "plugins",
}

EXCLUDE_PATTERNS = (
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    ".env",
    ".env.*",
    "*.dump",
)


def parse_password(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("SSH密码"):
            _, value = line.split("：", 1) if "：" in line else line.split(":", 1)
            return value.strip()
    raise RuntimeError("SSH password line not found.")


def parse_startup_database_url() -> str:
    text = STARTUP_FILE.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("$env:POSTGRES_DATABASE_URL"):
            _, value = line.split("=", 1)
            return value.strip().strip('"').strip("'")
    raise RuntimeError("POSTGRES_DATABASE_URL not found in startup file.")


def read_local_env() -> dict[str, str]:
    result: dict[str, str] = {}
    for env_path in [ROOT / "backend" / ".env", Path(r"D:\物流路径规划系统项目\backend\.env")]:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in {
                "AMAP_WEB_KEY",
                "AMAP_SERVICE_KEY",
                "AMAP_KEY",
                "TIANAPI_KEY",
                "TIANDITU_BROWSER_KEY",
                "TIANDITU_SERVER_KEY",
            }:
                result.setdefault(key, value)
    return result


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if not parts:
        return False
    if parts[0] in EXCLUDE_TOP_LEVEL:
        return True
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in EXCLUDE_PATTERNS)


def create_archive() -> Path:
    out = Path(tempfile.gettempdir()) / f"logistics-command-center-{int(time.time())}.tar.gz"
    include_roots = [
        "backend",
        "frontend",
        "miniprogram",
        "docs",
        "scripts",
        "docker-compose.prod.yml",
        "README.md",
    ]
    with tarfile.open(out, "w:gz") as tar:
        for item in include_roots:
            path = ROOT / item
            if not path.exists() or should_exclude(path):
                continue
            if path.is_file():
                tar.add(path, arcname=item)
                continue
            for child in path.rglob("*"):
                if should_exclude(child):
                    continue
                tar.add(child, arcname=str(child.relative_to(ROOT)))
    return out


def create_database_dump() -> Path:
    database_url = parse_startup_database_url()
    parsed = urlparse(database_url)
    dump_path = Path(tempfile.gettempdir()) / f"logistics_route_system_{int(time.time())}.dump"
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""
    command = [
        str(PG_DUMP),
        "-h",
        parsed.hostname or "localhost",
        "-p",
        str(parsed.port or 5432),
        "-U",
        parsed.username or "postgres",
        "-d",
        (parsed.path or "/logistics_route_system").lstrip("/"),
        "-F",
        "c",
        "--no-owner",
        "--no-acl",
        "-f",
        str(dump_path),
    ]
    subprocess.run(command, env=env, check=True)
    return dump_path


class Remote:
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self) -> None:
        self.client.connect(
            self.host,
            username=self.user,
            password=self.password,
            timeout=20,
            banner_timeout=20,
            auth_timeout=20,
            look_for_keys=False,
            allow_agent=False,
        )

    def close(self) -> None:
        self.client.close()

    def run(self, command: str, *, sudo: bool = False, timeout: int = 120, check: bool = True) -> str:
        wrapped = f"bash -lc {shlex.quote(command)}"
        if sudo:
            wrapped = f"sudo -S -p '' bash -lc {shlex.quote(command)}"
        stdin, stdout, stderr = self.client.exec_command(wrapped, get_pty=False, timeout=timeout)
        if sudo:
            stdin.write(self.password + "\n")
            stdin.flush()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        if check and code != 0:
            raise RuntimeError(f"Remote command failed ({code}): {command}\n{err or out}")
        return (out + err).strip()

    def upload(self, local_path: Path, remote_path: str) -> None:
        with self.client.open_sftp() as sftp:
            sftp.put(str(local_path), remote_path)


def build_env_file() -> str:
    local_env = read_local_env()
    amap_service_key = local_env.get("AMAP_SERVICE_KEY") or local_env.get("AMAP_KEY") or ""
    values = {
        "POSTGRES_DB": "logistics_route_system",
        "POSTGRES_USER": "logistics",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "SECRET_KEY": secrets.token_urlsafe(48),
        "JWT_SECRET_KEY": secrets.token_urlsafe(48),
        "AMAP_WEB_KEY": local_env.get("AMAP_WEB_KEY", ""),
        "AMAP_SERVICE_KEY": amap_service_key,
        "TIANAPI_KEY": local_env.get("TIANAPI_KEY", ""),
        "TIANDITU_BROWSER_KEY": local_env.get("TIANDITU_BROWSER_KEY", ""),
        "TIANDITU_SERVER_KEY": local_env.get("TIANDITU_SERVER_KEY", ""),
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def check_remote(remote: Remote) -> None:
    print("[1/6] Checking remote host...")
    print(remote.run("hostname && whoami && docker --version && docker compose version && df -h / && free -h", timeout=60))


def deploy(remote: Remote, *, skip_dump: bool = False) -> None:
    archive = create_archive()
    dump = None if skip_dump else create_database_dump()
    remote_archive = f"/home/{remote.user}/{archive.name}"
    remote_dump = f"/home/{remote.user}/{dump.name}" if dump else ""
    remote_env_tmp = f"/home/{remote.user}/.logistics-command-center-env.tmp"

    print(f"[2/6] Uploading code archive ({archive.stat().st_size / 1024 / 1024:.1f} MB)...")
    remote.upload(archive, remote_archive)
    if dump:
        print(f"[3/6] Uploading PostgreSQL dump ({dump.stat().st_size / 1024 / 1024:.1f} MB)...")
        remote.upload(dump, remote_dump)
    else:
        print("[3/6] Skipping PostgreSQL dump upload.")

    env_tmp = Path(tempfile.gettempdir()) / f"logistics-command-env-{int(time.time())}.tmp"
    env_tmp.write_text(build_env_file(), encoding="utf-8")
    try:
        remote.upload(env_tmp, remote_env_tmp)
    finally:
        env_tmp.unlink(missing_ok=True)

    print("[4/6] Preparing remote release directory...")
    remote.run(
        f"""
        set -e
        if ! swapon --show | grep -q '^'; then
          if [ ! -f /swapfile ]; then
            fallocate -l 2G /swapfile
            chmod 600 /swapfile
            mkswap /swapfile
          fi
          swapon /swapfile || true
          grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
        fi
        mkdir -p /opt/logistics-backups/nginx /opt/logistics-backups/releases
        rm -rf {REMOTE_RELEASE}.new
        mkdir -p {REMOTE_RELEASE}.new
        tar -xzf {shlex.quote(remote_archive)} -C {REMOTE_RELEASE}.new
        if [ -d {REMOTE_RELEASE} ]; then
          tar -czf /opt/logistics-backups/releases/logistics-route-system-$(date +%Y%m%d%H%M%S).tgz -C /opt logistics-route-system || true
        fi
        if [ -f {REMOTE_RELEASE}/.env.production ]; then
          cp {REMOTE_RELEASE}/.env.production /tmp/logistics-command-env.keep
        else
          cp {shlex.quote(remote_env_tmp)} /tmp/logistics-command-env.keep
        fi
        rm -rf {REMOTE_RELEASE}.previous
        if [ -d {REMOTE_RELEASE} ]; then
          mv {REMOTE_RELEASE} {REMOTE_RELEASE}.previous
        fi
        mv {REMOTE_RELEASE}.new {REMOTE_RELEASE}
        cp /tmp/logistics-command-env.keep {REMOTE_RELEASE}/.env.production
        chmod 600 {REMOTE_RELEASE}/.env.production
        mkdir -p {REMOTE_RELEASE}/logs
        rm -f {shlex.quote(remote_archive)} {shlex.quote(remote_env_tmp)}
        """,
        sudo=True,
        timeout=300,
    )

    compose = "docker compose --env-file .env.production -f docker-compose.prod.yml"
    print("[5/6] Restoring PostgreSQL data and building containers...")
    restore_snippet = ""
    restart_postgres = ":"
    if dump:
        restart_postgres = "docker rm -f logistics-postgres 2>/dev/null || true"
        restore_snippet = f"""
        docker cp {shlex.quote(remote_dump)} logistics-postgres:/tmp/logistics_route_system.dump
        {compose} exec -T postgres psql -U "${{POSTGRES_USER:-logistics}}" -d "${{POSTGRES_DB:-logistics_route_system}}" -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO \\"${{POSTGRES_USER:-logistics}}\\"; GRANT ALL ON SCHEMA public TO public;"
        {compose} exec -T postgres pg_restore -U "${{POSTGRES_USER:-logistics}}" -d "${{POSTGRES_DB:-logistics_route_system}}" --no-owner --no-acl /tmp/logistics_route_system.dump
        {compose} exec -T postgres rm -f /tmp/logistics_route_system.dump
        rm -f {shlex.quote(remote_dump)}
        """
    remote.run(
        f"""
        set -e
        cd {REMOTE_RELEASE}
        {restart_postgres}
        {compose} up -d postgres redis
        for i in $(seq 1 60); do
          if docker exec logistics-postgres pg_isready -U "${{POSTGRES_USER:-logistics}}" -d "${{POSTGRES_DB:-logistics_route_system}}" >/dev/null 2>&1; then
            break
          fi
          sleep 2
        done
        docker exec logistics-postgres pg_isready -U "${{POSTGRES_USER:-logistics}}" -d "${{POSTGRES_DB:-logistics_route_system}}"
        {restore_snippet}
        {compose} build
        docker stop backend frontend 2>/dev/null || true
        {compose} up -d
        docker cp logistics-frontend:/usr/share/nginx/html/. /usr/share/nginx/html/
        for conf in /etc/nginx/sites-enabled/logistics /etc/nginx/sites-enabled/logistics-demo-yu.top /etc/nginx/conf.d/logistics.conf; do
          if [ -e "$conf" ]; then
            cp "$conf" "/opt/logistics-backups/nginx/$(basename "$conf").bak.$(date +%Y%m%d%H%M%S)" || true
            sed -i 's#http://172\\.18\\.0\\.2:5000/api/#http://127.0.0.1:5000/api/#g' "$conf" || true
            sed -i 's#http://172\\.18\\.0\\.2:5000/socket.io/#http://127.0.0.1:5000/socket.io/#g' "$conf" || true
          fi
        done
        if [ -e /etc/nginx/sites-enabled/logistics ]; then
          mv /etc/nginx/sites-enabled/logistics "/opt/logistics-backups/nginx/logistics.disabled.$(date +%Y%m%d%H%M%S)" || true
        fi
        nginx -t
        systemctl reload nginx
        {compose} ps
        """,
        sudo=True,
        timeout=1800,
    )

    print("[6/6] Verifying deployment...")
    verify(remote)
    print("Deployment completed.")


def verify(remote: Remote) -> None:
    compose = "docker compose --env-file .env.production -f docker-compose.prod.yml"
    counts_code = (
        "from app import create_app; "
        "from app.models import Node, Route, Vehicle; "
        "from app.models.layered_data import ShipmentFact, RawLogisticsShipmentRecord; "
        "app=create_app('docker'); app.app_context().push(); "
        "print('shipment_facts', ShipmentFact.query.count()); "
        "print('raw_logistics_shipment_records', RawLogisticsShipmentRecord.query.count()); "
        "print('nodes', Node.query.count()); "
        "print('routes', Route.query.count()); "
        "print('vehicles', Vehicle.query.count())"
    )
    login_command = (
        "curl -s -o /tmp/logistics-login.json -w '%{http_code}' "
        "-X POST http://localhost/api/auth/login "
        "-H 'Content-Type: application/json' "
        "-d '{\"username\":\"admin\",\"password\":\"admin123\"}'; "
        "echo; "
        "python3 -c \"import json; d=json.load(open('/tmp/logistics-login.json')); "
        "print('has_token', bool(d.get('access_token') or d.get('token'))); "
        "print('user', (d.get('user') or {}).get('username'))\""
    )
    output = remote.run(
        f"""
        set -e
        cd {REMOTE_RELEASE}
        {compose} ps
        {compose} exec -T backend python -c {shlex.quote(counts_code)}
        curl -fsS http://localhost/api/health
        {login_command}
        curl -fsS http://localhost/api/health >/dev/null
        curl -I -s http://localhost:8080/ | head -5
        """,
        sudo=True,
        timeout=240,
    )
    print(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--skip-dump", action="store_true")
    parser.add_argument("--remote-command")
    args = parser.parse_args()

    socket.setdefaulttimeout(20)
    remote = Remote(args.host, args.user, parse_password(CREDS_FILE))
    try:
        remote.connect()
        check_remote(remote)
        if args.check_only:
            return 0
        if args.remote_command:
            print(remote.run(args.remote_command, sudo=True, timeout=300, check=False))
            return 0
        if args.verify:
            verify(remote)
            return 0
        deploy(remote, skip_dump=args.skip_dump)
    finally:
        remote.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
