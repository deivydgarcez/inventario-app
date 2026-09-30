import os
import json
import threading
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()


def _ts() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _cliente() -> str:
    try:
        from app.licenca import get_cliente_info
        nome, cnpj = get_cliente_info()
        if nome and cnpj:
            return f"{nome} ({cnpj})"
        return nome or cnpj or "Cliente não identificado"
    except Exception:
        return ""


def _enviar(payload: dict):
    if not _WEBHOOK:
        return
    data = json.dumps(payload).encode()
    req = Request(
        _WEBHOOK,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (Invec, 1.8.0)",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=5):
            pass
    except (URLError, Exception):
        pass  # Falha silenciosa — nunca bloqueia o fluxo principal


def _bg(payload: dict):
    threading.Thread(target=_enviar, args=(payload,), daemon=True).start()


def notificar_dispositivo_bloqueado(device_id: str, device_name: str, max_disp: int, usuario: str):
    _bg({
        "embeds": [{
            "title": "Dispositivo Bloqueado",
            "description": f"**{usuario}** tentou logar de um aparelho não autorizado.",
            "color": 0xCC2222,
            "fields": [
                {"name": "Loja / Cliente", "value": _cliente(), "inline": False},
                {"name": "Aparelho", "value": device_name, "inline": True},
                {"name": "Device ID", "value": f"`{device_id[:16]}…`", "inline": True},
                {"name": "Limite da licença", "value": f"{max_disp} dispositivo(s)", "inline": True},
            ],
            "footer": {"text": f"Invec Monitoramento • {_ts()}"},
        }]
    })


def notificar_dispositivo_novo(device_id: str, device_name: str, usuario: str):
    _bg({
        "embeds": [{
            "title": "Novo Dispositivo Registrado",
            "description": f"**{usuario}** logou pela primeira vez neste aparelho.",
            "color": 0x22AA44,
            "fields": [
                {"name": "Loja / Cliente", "value": _cliente(), "inline": False},
                {"name": "Aparelho", "value": device_name, "inline": True},
                {"name": "Device ID", "value": f"`{device_id[:16]}…`", "inline": True},
            ],
            "footer": {"text": f"Invec Monitoramento • {_ts()}"},
        }]
    })


def notificar_dispositivo_removido(device_id: str, device_name: str, removido_por: str):
    _bg({
        "embeds": [{
            "title": "Dispositivo Removido",
            "description": f"**{removido_por}** liberou um slot de dispositivo.",
            "color": 0xCC5B2A,
            "fields": [
                {"name": "Loja / Cliente", "value": _cliente(), "inline": False},
                {"name": "Aparelho", "value": device_name or "Desconhecido", "inline": True},
                {"name": "Device ID", "value": f"`{device_id[:16]}…`", "inline": True},
            ],
            "footer": {"text": f"Invec Monitoramento • {_ts()}"},
        }]
    })
