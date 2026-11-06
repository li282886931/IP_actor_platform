import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from fastapi import HTTPException, Request

from app.config import (WECHAT_API_TIMEOUT_SECONDS, WECHAT_MINIAPP_APPID, WECHAT_MINIAPP_MOCK_PHONE_NUMBER, WECHAT_MINIAPP_SECRET)


_wechat_access_token_cache = {
    "token": "",
    "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
}


def wechat_miniapp_appid():
    return os.environ.get('WECHAT_MINIAPP_APPID', WECHAT_MINIAPP_APPID).strip()


def wechat_miniapp_secret():
    return os.environ.get('WECHAT_MINIAPP_SECRET', WECHAT_MINIAPP_SECRET).strip()


LOCAL_DEVTOOLS_LOGIN_CODE = 'local-devtools-login-code'


LOCAL_DEVTOOLS_PHONE_CODE = 'local-devtools-phone-code'


LOCAL_DEVTOOLS_MOCK_PHONE_NUMBER = '13800000000'


def wechat_miniapp_mock_phone_number():
    return os.environ.get('WECHAT_MINIAPP_MOCK_PHONE_NUMBER', WECHAT_MINIAPP_MOCK_PHONE_NUMBER).strip()


def wechat_credentials_configured():
    return bool(wechat_miniapp_appid() and wechat_miniapp_secret())


def is_local_request(request: Optional[Request]):
    host = request.client.host if request and request.client else ''
    return host in {'127.0.0.1', '::1', 'testclient'}


def is_local_devtools_login(login_code: str, request: Optional[Request] = None):
    return bool(login_code) and is_local_request(request)


def is_local_devtools_phone(phone_code: str, request: Optional[Request] = None):
    return bool(phone_code) and is_local_request(request)


def exchange_wechat_login_code(login_code: str, request: Optional[Request] = None):
    if not login_code:
        raise HTTPException(status_code=400, detail='Missing wechat login code')
    if not wechat_credentials_configured():
        if wechat_miniapp_mock_phone_number() or is_local_devtools_login(login_code, request):
            digest = hashlib.sha256(login_code.encode('utf-8')).hexdigest()[:16]
            return {"openid": f"local-mock-openid-{digest}", "unionid": "", "session_key": "local-mock-session"}
        raise HTTPException(status_code=503, detail='WeChat miniapp credentials are not configured')
    try:
        response = requests.get(
            'https://api.weixin.qq.com/sns/jscode2session',
            params={
                "appid": wechat_miniapp_appid(),
                "secret": wechat_miniapp_secret(),
                "js_code": login_code,
                "grant_type": "authorization_code",
            },
            timeout=WECHAT_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f'WeChat login exchange failed: {exc}') from exc
    if payload.get('errcode'):
        raise HTTPException(status_code=502, detail=payload.get('errmsg') or 'WeChat login exchange failed')
    return payload


def get_wechat_access_token():
    now = datetime.now(timezone.utc)
    cached_token = _wechat_access_token_cache.get("token")
    expires_at = _wechat_access_token_cache.get("expires_at") or (now - timedelta(seconds=1))
    if cached_token and expires_at > now + timedelta(seconds=30):
        return cached_token
    if not wechat_credentials_configured():
        raise HTTPException(status_code=503, detail='WeChat miniapp credentials are not configured')
    try:
        response = requests.get(
            'https://api.weixin.qq.com/cgi-bin/token',
            params={
                "grant_type": "client_credential",
                "appid": wechat_miniapp_appid(),
                "secret": wechat_miniapp_secret(),
            },
            timeout=WECHAT_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f'WeChat access token request failed: {exc}') from exc
    if payload.get('errcode'):
        raise HTTPException(status_code=502, detail=payload.get('errmsg') or 'WeChat access token request failed')
    token = payload.get('access_token') or ''
    expires_in = int(payload.get('expires_in') or 0)
    if not token:
        raise HTTPException(status_code=502, detail='WeChat access token response is missing access_token')
    _wechat_access_token_cache["token"] = token
    _wechat_access_token_cache["expires_at"] = now + timedelta(seconds=max(expires_in - 60, 60))
    return token


def fetch_wechat_phone_number(phone_code: str, request: Optional[Request] = None):
    if not phone_code:
        raise HTTPException(status_code=400, detail='Missing wechat phone code')
    if not wechat_credentials_configured():
        mock_phone = wechat_miniapp_mock_phone_number()
        if mock_phone:
            return mock_phone
        if is_local_devtools_phone(phone_code, request):
            return LOCAL_DEVTOOLS_MOCK_PHONE_NUMBER
        raise HTTPException(status_code=503, detail='WeChat miniapp credentials are not configured')
    access_token = get_wechat_access_token()
    try:
        response = requests.post(
            f'https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={access_token}',
            json={"code": phone_code},
            timeout=WECHAT_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f'WeChat phone number request failed: {exc}') from exc
    if payload.get('errcode'):
        raise HTTPException(status_code=502, detail=payload.get('errmsg') or 'WeChat phone number request failed')
    phone_info = payload.get('phone_info') or {}
    phone_number = phone_info.get('purePhoneNumber') or phone_info.get('phoneNumber') or ''
    if not phone_number:
        raise HTTPException(status_code=502, detail='WeChat phone number response is missing phone number')
    return phone_number
