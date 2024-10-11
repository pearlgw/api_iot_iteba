
# new codingan
from sqlalchemy import create_engine, text # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends # type: ignore
from fastapi.responses import FileResponse # type: ignore
import uuid
import os
from dotenv import load_dotenv # type: ignore

load_dotenv('.env')

IMAGEDIR = "images/"

# Buat engine SQLAlchemy untuk koneksi pool
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_DATABASE')}"

engine = create_engine(DATABASE_URL, pool_recycle=3600)  # Atur pool recycle time agar koneksi diperbarui setiap jam
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# Dependency untuk mendapatkan session database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get('/')
def read_root():
    return {"Hello": "World"} 

@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...), db: SessionLocal = Depends(get_db)): # type: ignore
    # buat nama file pake uuid
    file.filename = f"{uuid.uuid4()}.jpg"
    contents = await file.read()

    # Simpan di direktori
    file_path = os.path.join(IMAGEDIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Simpan database
    try:
        # Gunakan text() untuk SQL mentah
        sql = text("INSERT INTO images (filename, filepath) VALUES (:filename, :filepath)")
        db.execute(sql, {"filename": file.filename, "filepath": file_path})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving image to database: {str(e)}")

    return {"filename": file.filename, "filepath": file_path}

@app.get("/show/")
async def show_image(filename: str):
    # Path file gambar
    file_path = os.path.join(IMAGEDIR, filename)

    # Cek file yang ada di direktori images
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)
