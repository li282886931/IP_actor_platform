from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .services import init_db


def create_app():
    app = FastAPI(title='锐音场 Backend')

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
init_db()
