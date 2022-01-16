# Xbox Live Minecraft Auth Test

This is a test web application for authenticating with Mojang/Minecraft via
Xbox Live and OAuth2.

The login flow was mostly implemented using [wiki.vg](https://wiki.vg/Microsoft_Authentication_Scheme) as a guide.

## Prerequisites
Before starting, you will first need to obtain an
[OAuth 2.0](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
Client ID & secret by creating a
[Microsoft Azure application](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app). 

When prompted, use http://localhost/oauth2-callback as the redirect uri

## Configuring

After obtaining your client id and secret, create a file named `.env` with the following values:

```
XBOXLIVE_CLIENT_ID=<client_id>
XBOXLIVE_CLIENT_SECRET=<client_secret>
```

## Running

Use [poetry](https://python-poetry.org) to install dependencies and run

```shell
poetry install
poetry shell

uvicorn main:app
# or
python main.py
```
