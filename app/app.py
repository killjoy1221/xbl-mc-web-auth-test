from fastapi import Depends, FastAPI, Request, HTTPException
from starlette.middleware.sessions import SessionMiddleware

from .models import MinecraftProfile
from . import auth
from .templates import templates

app = FastAPI(
    title="Xbox Live Minecraft Web Auth Test",
    version="1.0",
)
app.add_middleware(SessionMiddleware, secret_key="secret")
app.include_router(auth.router)


@app.get("/")
async def root(request: Request, profile: MinecraftProfile | None = Depends(auth.get_user_profile)):
    context = {
        "request": request,
        "profile": profile,
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/user", response_model=MinecraftProfile)
async def get_user_profile(profile: MinecraftProfile | None = Depends(auth.get_user_profile)):
    if profile is None:
        raise HTTPException(401)
    return profile


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True, debug=True)
