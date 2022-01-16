import datetime
import enum

import httpx
from pydantic import BaseModel

from .models import MinecraftProfile

XBOX_AUTH_BASE = "https://{0}.auth.xboxlive.com/{0}/{1}"
XBOX_USER_AUTH = XBOX_AUTH_BASE.format("user", "authenticate")
XBOX_XSTS_AUTH = XBOX_AUTH_BASE.format("xsts", "authorize")

MC_BASE = "https://api.minecraftservices.com/"
MC_AUTH_XBOX = MC_BASE + "authentication/login_with_xbox"
MC_PROFILE = MC_BASE + "minecraft/profile"


class XboxAuth(BaseModel):
    IssueInstant: datetime.datetime
    NotAfter: datetime.datetime
    Token: str
    DisplayClaims: dict[str, list[dict[str, str]]]


class XError(enum.IntEnum):
    NO_ACCOUNT = 2148916233
    REGION = 2148916235
    CHILD = 2148916238


class XSTSError(BaseModel):
    Identity: str
    XErr: XError
    Message: str
    Redirect: str


class MinecraftAuth(BaseModel):
    username: str
    roles: list
    access_token: str
    token_type: str
    expires_in: int


class AuthFlow:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def auth_xbl(self, access_token: str) -> XboxAuth:
        response = await self.client.post(
            XBOX_USER_AUTH,
            json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={access_token}",
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT",
            },
        )

        return XboxAuth.parse_obj(response.json())

    async def auth_xsts(self, xbox_auth: XboxAuth) -> XboxAuth | XSTSError:
        response = await self.client.post(
            XBOX_XSTS_AUTH,
            json={
                "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbox_auth.Token]},
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType": "JWT",
            },
        )
        cls = XboxAuth
        if response.is_client_error:
            cls = XSTSError

        return cls.parse_obj(response.json())

    async def auth_minecraft(self, xbox_auth: XboxAuth) -> MinecraftAuth:
        userhash, xsts_token = xbox_auth.DisplayClaims["xui"][0]["uhs"], xbox_auth.Token
        response = await self.client.post(
            MC_AUTH_XBOX,
            json={"identityToken": f"XBL3.0 x={userhash};{xsts_token}"},
        )
        return MinecraftAuth.parse_obj(response.json())

    async def get_minecraft_profile(self, mc_auth: MinecraftAuth) -> MinecraftProfile:
        response = await self.client.get(
            MC_PROFILE,
            headers={"Authorization": f"Bearer {mc_auth.access_token}"},
        )
        return MinecraftProfile.parse_obj(response.json())

    async def login(self, xbl_access_token: str) -> MinecraftProfile:
        """Start the lengthy authorization process."""
        response = await self.auth_xbl(xbl_access_token)
        response = await self.auth_xsts(response)
        if isinstance(response, XSTSError):
            raise XboxLoginError(response)
        response = await self.auth_minecraft(response)

        return await self.get_minecraft_profile(response)


async def fetch_minecraft_profile(xbl_access_token: str) -> MinecraftProfile:
    async with httpx.AsyncClient() as client:
        flow = AuthFlow(client)
        return await flow.login(xbl_access_token)


class XboxLoginError(Exception):
    def __init__(self, err: XSTSError):
        self.err = err
        super().__init__(str(err))
