"""Carga y acceso a la configuración (config.yaml + .env)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.yaml"


class Config:
    """Acceso tipado y por puntos a la configuración del proyecto."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # --- acceso genérico -------------------------------------------------
    def get(self, path: str, default: Any = None) -> Any:
        """Lee una clave anidada con notación de puntos: cfg.get('llm.model')."""
        node: Any = self._data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    # --- secretos (.env) -------------------------------------------------
    @property
    def deepseek_api_key(self) -> str:
        key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "Falta DEEPSEEK_API_KEY. Copia .env.example a .env y pega tu clave."
            )
        return key

    @property
    def deepseek_base_url(self) -> str:
        return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()

    @property
    def has_api_key(self) -> bool:
        return bool(os.getenv("DEEPSEEK_API_KEY", "").strip())

    @property
    def raw(self) -> dict[str, Any]:
        return self._data


def load_config(path: Path = CONFIG_PATH) -> Config:
    load_dotenv(ROOT_DIR / ".env")
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return Config(data)


# Instancia compartida
config = load_config()
