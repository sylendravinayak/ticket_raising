from fastapi import FastAPI

from src.api.middleware.cors import setup_cors


def register_middlewares(app: FastAPI)->None:
    app.add_middleware(setup_cors(app))
