#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Provider key resolution without exposing secret values."""

import os
from typing import Dict, Iterable, Tuple

try:
    from flask import current_app
except Exception:  # pragma: no cover - flask may be unavailable in utility contexts
    current_app = None


AMAP_WEB_ALIASES = (
    "AMAP_WEB_KEY",
    "AMAP_BROWSER_KEY",
    "AMAP_JS_KEY",
    "GAODE_WEB_KEY",
    "GAODE_BROWSER_KEY",
    "GAODE_FRONTEND_KEY",
    "GAODE_MAP_FRONTEND_KEY",
)

AMAP_SERVICE_ALIASES = (
    "AMAP_SERVICE_KEY",
    "AMAP_KEY",
    "GAODE_SERVICE_KEY",
    "GAODE_MAP_KEY",
    "GAODE_REST_KEY",
    "GAODE_BACKEND_KEY",
    "GAODE_MAP_BACKEND_KEY",
)

TIANDITU_BROWSER_ALIASES = (
    "TIANDITU_BROWSER_KEY",
    "TIANDITU_WEB_KEY",
    "TIANDITU_JS_KEY",
    "TDT_BROWSER_KEY",
    "TDT_WEB_KEY",
)

TIANDITU_SERVER_ALIASES = (
    "TIANDITU_SERVER_KEY",
    "TIANDITU_KEY",
    "TIANDITU_API_KEY",
    "TDT_SERVER_KEY",
    "TDT_KEY",
    "TDT_API_KEY",
)


def resolve_env(names: Iterable[str]) -> Tuple[str, str]:
    """Return the first configured value and its source variable name."""
    config = {}
    if current_app is not None:
        try:
            config = current_app.config
        except RuntimeError:
            config = {}

    for name in names:
        value = config.get(name) if config else None
        if value is None:
            value = os.environ.get(name)
        if value is not None and str(value).strip():
            return str(value).strip(), name
    return "", None


def get_amap_keys() -> Dict:
    web_key, web_source = resolve_env(AMAP_WEB_ALIASES)
    service_key, service_source = resolve_env(AMAP_SERVICE_ALIASES)
    return {
        "web_key": web_key,
        "web_key_source": web_source,
        "service_key": service_key,
        "service_key_source": service_source,
        "effective_key": service_key or web_key,
        "effective_key_source": service_source or web_source,
    }


def get_tianditu_keys() -> Dict:
    browser_key, browser_source = resolve_env(TIANDITU_BROWSER_ALIASES)
    server_key, server_source = resolve_env(TIANDITU_SERVER_ALIASES)
    return {
        "browser_key": browser_key,
        "browser_key_source": browser_source,
        "server_key": server_key,
        "server_key_source": server_source,
        "effective_key": server_key or browser_key,
        "effective_key_source": server_source or browser_source,
    }


def provider_key_status(provider: str, keys: Dict) -> Dict:
    """Build a safe key status payload. Values are intentionally omitted."""
    if provider == "amap":
        return {
            "provider": "amap",
            "web_key_configured": bool(keys.get("web_key")),
            "web_key_source": keys.get("web_key_source"),
            "service_key_configured": bool(keys.get("service_key")),
            "service_key_source": keys.get("service_key_source"),
            "effective_key_configured": bool(keys.get("effective_key")),
            "effective_key_source": keys.get("effective_key_source"),
        }

    if provider == "tianditu":
        return {
            "provider": "tianditu",
            "browser_key_configured": bool(keys.get("browser_key")),
            "browser_key_source": keys.get("browser_key_source"),
            "server_key_configured": bool(keys.get("server_key")),
            "server_key_source": keys.get("server_key_source"),
            "effective_key_configured": bool(keys.get("effective_key")),
            "effective_key_source": keys.get("effective_key_source"),
        }

    return {
        "provider": provider,
        "effective_key_configured": bool(keys.get("effective_key")),
        "effective_key_source": keys.get("effective_key_source"),
    }
