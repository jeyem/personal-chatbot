from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Config
from .db import init_db
from .router import router
from .state import set_states


def init_app(cfg: Config):
    set_states(cfg)
    init_db(cfg.DATABASE_URL)

    app = FastAPI(title=cfg.ENV, debug=cfg.DEBUG)

    if not cfg.DEBUG:
        from .middlewares import ProtectionMiddleware

        app.add_middleware(ProtectionMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.APP.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app
