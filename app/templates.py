from urllib.parse import urlparse

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates("templates")


def is_link(s):
    if isinstance(s, str):
        result = urlparse(s)
        return result.scheme in ("http", "https") and result.hostname
    return False


templates.env.tests["link"] = is_link
