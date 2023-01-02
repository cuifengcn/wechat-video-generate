from fastapi import FastAPI
from pathlib import Path
from starlette.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from utils import MAIN_PATH

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=MAIN_PATH.joinpath("weixin_chat", "static")),
    name="static",
)


@app.route("/")
def index(*args, **kwargs):
    return HTMLResponse(
        MAIN_PATH.joinpath(
            "weixin_chat",
            "index.html",
        ).read_text(encoding="utf-8")
    )


@app.route("/favicon.png")
def icon(*args, **kwargs):
    return FileResponse(MAIN_PATH.joinpath("weixin_chat", "favicon.png"))


# if __name__ == "__main__":
#     import uvicorn
#
#     uvicorn.run(app, host="127.0.0.1", port=36999)
