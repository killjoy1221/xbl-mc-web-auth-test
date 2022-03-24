from authlib.integrations.starlette_client import OAuth, OAuthError, StarletteRemoteApp
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseSettings, ValidationError

from . import mcauth
from .models import MinecraftProfile
from .templates import templates


class XboxConfig(BaseSettings):
    client_id: str
    client_secret: str

    server_metadata_url: str = "https://login.live.com/.well-known/openid-configuration"
    client_kwargs: dict = {"scope": "XboxLive.signin offline_access"}

    class Config:
        env_prefix = "XBOXLIVE_"
        env_file = ".env"


router = APIRouter()

try:
    config = XboxConfig()
except ValidationError:
    raise RuntimeError(
        """Environment is mis-configured!

To configure the environment, create a file named .env and fill it with the
following values.

    XBOXLIVE_CLIENT_ID=<client_id>
    XBOXLIVE_CLIENT_SECRET=<client_secret>
    """
    )

xboxlive: StarletteRemoteApp = OAuth().register(
    "xboxlive",
    **XboxConfig().dict(),
)


def get_user_profile(request: Request) -> MinecraftProfile | None:
    if "profile" in request.session:
        return MinecraftProfile.parse_raw(request.session["profile"])


def set_user_profile(request: Request, profile: MinecraftProfile):
    request.session["profile"] = profile.json()


@router.route("/login")
async def login(request: Request):
    request.session.clear()
    callback = request.url_for("login_callback")
    return await xboxlive.authorize_redirect(request, callback)


@router.route("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(request.url_for("root"))


@router.route("/oauth2-callback")
async def login_callback(request: Request):
    try:
        token = await xboxlive.authorize_access_token(request)
        profile = await mcauth.fetch_minecraft_profile(token["access_token"])
        set_user_profile(request, profile)
        return RedirectResponse(request.url_for("root"))
    except OAuthError as e:
        request.session.clear()
        request.session["login-error"] = str(e)
    except mcauth.XboxLoginError as e:
        request.session.clear()
        message = get_x_error_message(e.err.XErr)
        request.session["login-error"] = f"{e.err.XErr}: {message}"
    return RedirectResponse(request.url_for("login_error"))


def get_x_error_message(code: mcauth.XError):
    match code:
        case mcauth.XError.NO_ACCOUNT:
            return "This account is not associated with a Xbox Live account."
        case mcauth.XError.REGION:
            return "This account is in a region where Xbox Live is not available."
        case mcauth.XError.CHILD:
            return "This account is a child and must be added to a Family."


@router.route("/login-error")
async def login_error(request: Request):
    if "login-error" in request.session:
        error = request.session.pop("login-error")
        return templates.TemplateResponse(
            "login-error.html", {"request": request, "message": error}
        )

    return RedirectResponse(request.url_for("root"))
