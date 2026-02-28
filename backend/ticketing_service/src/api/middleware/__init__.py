from fastapi import FastAPI
from src.api.middleware.request_id import RequestIDMiddleware
from src.api.middleware.cors import setup_cors

def register_middlewares(app: FastAPI):
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(setup_cors(app))
