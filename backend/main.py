from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine

app = FastAPI()


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "NovelMatch backend is running"}


# @app.get("/supabase-check")
# async def supabase_check() -> dict[str, object]:
#     try:
#         async with engine.connect() as connection:
#             result = await connection.execute(text("SELECT 1"))
#             return {
#                 "connected": result.scalar_one() == 1,
#                 "message": "Supabase database connection is working",
#             }
#     except SQLAlchemyError as exc:
#         raise HTTPException(
#             status_code=503,
#             detail=f"Supabase database connection failed: {exc}",
#         ) from exc
