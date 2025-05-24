from typing import Any, Dict

import requests
from django.conf import settings
from google.oauth2 import id_token
from rest_framework.exceptions import APIException

GOOGLE_ID_TOKEN_INFO_URL = "https://www.googleapis.com/oauth2/v3/tokeninfo"
GOOGLE_ACCESS_TOKEN_OBTAIN_URL = "https://accounts.google.com/o/oauth2/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def google_get_user_data(validated_data):
    if validated_data.get("code"):
        return google_get_user_data_web(code=validated_data["code"])
    else:
        return google_get_user_data_mobile(token=validated_data["token"])


def google_get_user_data_web(code):
    # https://github.com/MomenSherif/react-oauth/issues/252
    redirect_uri = "postmessage"
    access_token = google_get_access_token(code=code, redirect_uri=redirect_uri)
    return google_get_user_info(access_token=access_token)


def google_get_user_data_mobile(token):
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request())

        return {
            "email": idinfo["email"],
            "given_name": idinfo.get("given_name", ""),
            "family_name": idinfo.get("family_name", ""),
            "sub": idinfo["sub"],
        }
    except ValueError:
        raise Exception("ID token inválido")


# Exchange authorization token with access token
# https://developers.google.com/identity/protocols/oauth2/web-server#obtainingaccesstokens
def google_get_access_token(code: str, redirect_uri: str) -> str:
    data = {
        "code": code,
        "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    response = requests.post(GOOGLE_ACCESS_TOKEN_OBTAIN_URL, data=data)
    if not response.ok:
        raise APIException(f"Could not get access token from Google: {response.json()}")

    access_token = response.json()["access_token"]

    return access_token


# Get user info from google
# https://developers.google.com/identity/protocols/oauth2/web-server#callinganapi
def google_get_user_info(access_token: str) -> Dict[str, Any]:
    response = requests.get(
        GOOGLE_USER_INFO_URL,
        params={"access_token": access_token},
    )

    if not response.ok:
        raise APIException("Could not get user info from Google: {response.json()}")

    return response.json()
