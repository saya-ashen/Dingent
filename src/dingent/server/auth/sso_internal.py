from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode
from xml.etree import ElementTree

import aiohttp
from fastapi import HTTPException, Request, status

from dingent.server.auth.sso import SSOProfile

_CAS_SERVER_BASE_URL = "https://sso.cncb.ac.cn"
_CAS_LOGIN_URL = f"{_CAS_SERVER_BASE_URL}/login"
_CAS_VALIDATE_URL = f"{_CAS_SERVER_BASE_URL}/serviceValidate"


class InternalCASProvider:
    name = os.getenv("INTERNAL_SSO_PROVIDER_NAME", "internal-cas")

    def __init__(self) -> None:
        self.login_url = os.getenv("INTERNAL_SSO_LOGIN_URL", _CAS_LOGIN_URL)
        self.validate_url = os.getenv("INTERNAL_SSO_VALIDATE_URL", _CAS_VALIDATE_URL)
        self.timeout_seconds = int(os.getenv("INTERNAL_SSO_TIMEOUT_SECONDS", "10"))
        self.subject_attribute = os.getenv("INTERNAL_SSO_SUBJECT_ATTRIBUTE", "userId")
        self.email_attribute = os.getenv("INTERNAL_SSO_EMAIL_ATTRIBUTE", "email")
        self.username_attribute = os.getenv("INTERNAL_SSO_USERNAME_ATTRIBUTE", "username")
        self.display_name_attribute = os.getenv("INTERNAL_SSO_DISPLAY_NAME_ATTRIBUTE", "displayName")

    def build_login_redirect_url(self, *, request: Request, next_url: str | None = None) -> str:
        service_url = self._service_url(request=request, next_url=next_url)
        return f"{self.login_url}?{urlencode({'service': service_url})}"

    async def authenticate_callback(self, *, request: Request) -> SSOProfile:
        ticket = request.query_params.get("ticket")
        if not ticket:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CAS callback requires ticket")

        service_url = self._service_url(request=request, next_url=request.query_params.get("next"))
        validate_url = f"{self.validate_url}?{urlencode({'service': service_url, 'ticket': ticket})}"

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(validate_url) as response:
                    payload = await response.read()
        except (aiohttp.ClientError, TimeoutError) as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="CAS server unreachable") from error

        return self.parse_profile(payload)

    def parse_profile(self, payload: bytes) -> SSOProfile:
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid CAS response") from error

        namespace = {"cas": "http://www.yale.edu/tp/cas"}
        success = root.find("cas:authenticationSuccess", namespace)
        if success is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CAS authentication failed")

        cas_user = self._cas_user(success=success, namespace=namespace)
        attributes = self._cas_attributes(success=success, namespace=namespace)

        subject = self._clean(attributes.get(self.subject_attribute)) or cas_user
        email = self._clean(attributes.get(self.email_attribute)) or (cas_user if "@" in cas_user else None)
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CAS profile does not include an email address")

        username = self._clean(attributes.get(self.username_attribute)) or email.split("@", maxsplit=1)[0]
        display_name = self._clean(attributes.get(self.display_name_attribute))

        return SSOProfile(
            provider=self.name,
            subject=subject,
            email=email,
            username=username,
            display_name=display_name,
            attributes={"cas_user": cas_user, "cas_attributes": attributes},
        )

    def _service_url(self, *, request: Request, next_url: str | None = None) -> str:
        service_url = str(request.url_for("sso_callback"))
        if next_url:
            service_url = f"{service_url}?{urlencode({'next': next_url})}"
        return service_url

    def _cas_user(self, *, success: ElementTree.Element, namespace: dict[str, str]) -> str:
        user_element = success.find("cas:user", namespace)
        cas_user = self._clean(user_element.text if user_element is not None else None)
        if not cas_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CAS response does not include a user")
        return cas_user

    def _cas_attributes(self, *, success: ElementTree.Element, namespace: dict[str, str]) -> dict[str, Any]:
        attributes: dict[str, Any] = {}
        attributes_element = success.find("cas:attributes", namespace)
        if attributes_element is None:
            return attributes

        for child in attributes_element:
            key = child.tag.rsplit("}", maxsplit=1)[-1]
            attributes[key] = child.text
        return attributes

    @staticmethod
    def _clean(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
