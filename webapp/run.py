"""서버 실행: python -m webapp.run"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("webapp.main:app", host="0.0.0.0", port=8000, reload=True)
