#
#  Copyright (c) 2026
#  Thin HTTP client for Jasmin's REST-ish HTTP API (port 1401) and RESTful API (8080).
#
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SUCCESS_MSG_ID_RE = re.compile(r'Success\s+"?([^"\s]+)"?', re.IGNORECASE)


@dataclass
class JasminHttpResult:
    ok: bool
    text: str
    message_id: str = ""
    status_code: int = 0
    error: str = ""
    data: Optional[dict] = None


class JasminHttpClient:
    """
    Client for Jasmin HTTP API endpoints:
      POST /send
      GET  /balance
      GET  /rate
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or settings.JASMIN_HTTP_API_URL).rstrip("/") + "/"
        self.timeout = timeout if timeout is not None else getattr(settings, "JASMIN_HTTP_API_TIMEOUT", 15)

    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    def send(
        self,
        *,
        username: str,
        password: str,
        to: str,
        content: str,
        from_addr: str = "",
        coding: int = 0,
        priority: int = 0,
        dlr: str = "yes",
        dlr_level: int = 3,
        dlr_url: str = "",
        dlr_method: str = "POST",
    ) -> JasminHttpResult:
        payload = {
            "username": username,
            "password": password,
            "to": to,
            "content": content,
            "coding": coding,
            "priority": priority,
            "dlr": dlr,
            "dlr-level": dlr_level,
            "dlr-method": dlr_method,
        }
        if from_addr:
            payload["from"] = from_addr
        if dlr_url:
            payload["dlr-url"] = dlr_url

        return self._post("send", payload, parse_msg_id=True)

    def balance(self, *, username: str, password: str) -> JasminHttpResult:
        return self._get("balance", {"username": username, "password": password})

    def rate(self, *, username: str, password: str, to: str = "") -> JasminHttpResult:
        params = {"username": username, "password": password}
        if to:
            params["to"] = to
        return self._get("rate", params)

    def _post(self, path: str, data: dict, parse_msg_id: bool = False) -> JasminHttpResult:
        url = self._url(path)
        try:
            response = requests.post(url, data=data, timeout=self.timeout)
            text = (response.text or "").strip()
            msg_id = ""
            if parse_msg_id:
                match = SUCCESS_MSG_ID_RE.search(text)
                if match:
                    msg_id = match.group(1)
            ok = response.status_code == 200 and text.lower().startswith("success")
            return JasminHttpResult(
                ok=ok,
                text=text,
                message_id=msg_id,
                status_code=response.status_code,
                error="" if ok else text or f"HTTP {response.status_code}",
            )
        except requests.RequestException as exc:
            logger.exception("Jasmin HTTP /%s failed", path)
            return JasminHttpResult(ok=False, text="", error=str(exc), status_code=0)

    def _get(self, path: str, params: dict) -> JasminHttpResult:
        url = self._url(path)
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            text = (response.text or "").strip()
            ok = response.status_code == 200
            return JasminHttpResult(
                ok=ok,
                text=text,
                status_code=response.status_code,
                error="" if ok else text or f"HTTP {response.status_code}",
            )
        except requests.RequestException as exc:
            logger.exception("Jasmin HTTP /%s failed", path)
            return JasminHttpResult(ok=False, text="", error=str(exc), status_code=0)


class JasminRestClient:
    """
    Client for Jasmin RESTful API (Basic Auth):
      POST /secure/send
      POST /secure/sendbatch
    """

    def __init__(self, base_url: str, timeout: Optional[float] = None):
        self.base_url = (base_url or "").rstrip("/") + "/"
        self.timeout = timeout if timeout is not None else getattr(settings, "JASMIN_HTTP_API_TIMEOUT", 30)

    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    def send(
        self,
        *,
        username: str,
        password: str,
        to: str,
        content: str,
        from_addr: str = "",
        dlr_level: int = 3,
        dlr_url: str = "",
        dlr_method: str = "POST",
        priority: int = 0,
    ) -> JasminHttpResult:
        body: dict[str, Any] = {
            "to": to,
            "content": content,
            "dlr": "yes",
            "dlr-level": dlr_level,
            "dlr-method": dlr_method,
            "priority": priority,
        }
        if from_addr:
            body["from"] = from_addr
        if dlr_url:
            body["dlr-url"] = dlr_url
        return self._json_post("secure/send", username, password, body, parse_msg_id=True)

    def sendbatch(
        self,
        *,
        username: str,
        password: str,
        messages: list[dict],
        globals_: Optional[dict] = None,
        batch_config: Optional[dict] = None,
    ) -> JasminHttpResult:
        body: dict[str, Any] = {"messages": messages}
        if globals_:
            body["globals"] = globals_
        if batch_config:
            body["batch_config"] = batch_config
        return self._json_post("secure/sendbatch", username, password, body)

    def ping(self) -> JasminHttpResult:
        url = self._url("ping")
        try:
            response = requests.get(url, timeout=self.timeout)
            text = (response.text or "").strip()
            ok = response.status_code == 200
            return JasminHttpResult(ok=ok, text=text, status_code=response.status_code)
        except requests.RequestException as exc:
            return JasminHttpResult(ok=False, text="", error=str(exc), status_code=0)

    def _json_post(
        self,
        path: str,
        username: str,
        password: str,
        body: dict,
        parse_msg_id: bool = False,
    ) -> JasminHttpResult:
        url = self._url(path)
        try:
            response = requests.post(
                url,
                json=body,
                auth=(username, password),
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            text = (response.text or "").strip()
            data = None
            try:
                data = response.json()
            except ValueError:
                data = None

            msg_id = ""
            if parse_msg_id and isinstance(data, dict):
                raw = data.get("data") or ""
                match = SUCCESS_MSG_ID_RE.search(str(raw))
                if match:
                    msg_id = match.group(1)

            ok = response.status_code == 200
            error = ""
            if not ok:
                if isinstance(data, dict):
                    error = str(data.get("message") or data.get("error") or text)
                else:
                    error = text or f"HTTP {response.status_code}"

            return JasminHttpResult(
                ok=ok,
                text=text,
                message_id=msg_id,
                status_code=response.status_code,
                error=error,
                data=data if isinstance(data, dict) else None,
            )
        except requests.RequestException as exc:
            logger.exception("Jasmin REST /%s failed", path)
            return JasminHttpResult(ok=False, text="", error=str(exc), status_code=0)
