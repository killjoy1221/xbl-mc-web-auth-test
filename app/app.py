#!/usr/bin/env python
import http
from urllib.parse import urlparse

import authlib.integrations.base_client
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware

import mcauth

templates = Jinja2Templates("templates")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="secret")

oauth = OAuth(Config(".env"))
oauth.register(
    "xboxlive",
    server_metadata_url="https://login.live.com/.well-known/openid-configuration",
    client_kwargs={"scope": "XboxLive.signin offline_access"},
)


def is_link(s):
    if isinstance(s, str):
        result = urlparse(s)
        return result.scheme in ("http", "https") and result.hostname
    return False


templates.env.tests["link"] = is_link


def get_user_profile(request: Request) -> mcauth.MinecraftProfile | None:
    if "profile" in request.session:
        return mcauth.MinecraftProfile.parse_raw(request.session["profile"])


def set_user_profile(request: Request, profile: mcauth.MinecraftProfile):
    request.session["profile"] = profile.json()


@app.get("/")
async def root(request: Request):
    profile = get_user_profile(request)
    if profile is None:
        return RedirectResponse(request.url_for("login"))
    return templates.TemplateResponse(
        "index.html", {"request": request, "profile": profile}
    )


@app.get("/login")
async def login(request: Request):
    request.session.clear()
    callback = request.url_for("login_callback")
    return await oauth.xboxlive.authorize_redirect(request, callback)


@app.get("/logout", status_code=http.HTTPStatus.NO_CONTENT)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(request.url_for("root"))


@app.get("/oauth2-callback")
async def login_callback(request: Request):
    try:
        token = await oauth.xboxlive.authorize_access_token(request)
        profile = await mcauth.fetch_minecraft_profile(token["access_token"])
        set_user_profile(request, profile)
        return RedirectResponse(request.url_for("root"))
    except authlib.integrations.base_client.OAuthError as e:
        request.session.clear()
        request.session["login-error"] = str(e)
    except mcauth.XboxLoginError as e:
        request.session.clear()
        request.session["login-error"] = get_x_error_message(e.err.XErr)
    return RedirectResponse(request.url_for("login_error"))


def get_x_error_message(code: mcauth.XError):
    match code:
        case mcauth.XError.NO_ACCOUNT:
            return f"{code}: This account is not associated with a Xbox Live account."
        case mcauth.XError.REGION:
            return (
                f"{code}: This account is in a region where Xbox Live is not available."
            )
        case mcauth.XError.CHILD:
            return f"{code}: This account is a child and must be added to a Family before proceeding."


@app.get("/login-error")
async def login_error(request: Request):
    if "login-error" in request.session:
        error = request.session.pop("login-error")
        return templates.TemplateResponse(
            "login-error.html", {"request": request, "message": error}
        )

    return RedirectResponse(request.url_for("root"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True, debug=True)
