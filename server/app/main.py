from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.user_manager.routes import user_manager_router
from app.quiz_manager.routes import quiz_manager_router
from app.database.database import client
import logging
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

try:
    client.admin.command('ping')
    print('✅ Successfully connected to the database!')
    app = FastAPI(debug=False)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    app.include_router(user_manager_router)
    app.include_router(quiz_manager_router)
    app.mount('/uploads', StaticFiles(directory=os.path.abspath('uploads')), name='uploads')

    @app.get('/', tags=['Ping'])
    def read_root():
        return {'detail': 'FastAPI'}

except Exception as e:
    print(f'❌ Database connection error: {e}')
