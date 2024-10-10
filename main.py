from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException, Form # type: ignore
import uuid
from fastapi.responses import FileResponse # type: ignore
import os
from sqlalchemy import create_engine, Column, Integer, String # type: ignore
from sqlalchemy.orm import sessionmaker, declarative_base # type: ignore
from dotenv import load_dotenv # type: ignore
from pydantic import BaseModel # type: ignore

load_dotenv('.env')

# Setup database URL
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@" \
               f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_DATABASE')}"

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model definition
class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(255), nullable=False)
    device_id = Column(String(255), nullable=False)

# Model Pydantic untuk response
class ImageResponse(BaseModel):
    # id: int
    filename: str
    filepath: str
    device_id: str

    class Config:
        orm_mode = True

IMAGEDIR = "images/"
app = FastAPI()

@app.get('/')
def read_root():
    return {"message": "Hallo Selamat Datang di API IoT Iteba"} 

@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...), device_id: str = Form(...)):
    # Buat nama file pake uuid
    file.filename = f"{uuid.uuid4()}.jpg"
    contents = await file.read()

    # Simpan file di direktori
    file_path = os.path.join(IMAGEDIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Simpan ke database
    db = SessionLocal()
    try:
        new_image = Image(filename=file.filename, filepath=file_path, device_id=device_id)
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving image to database: {str(e)}")
    finally:
        db.close()

    return {
        "filename": file.filename,
        "filepath": file_path,
        "device_id": device_id
    }

@app.get("/images/", response_model=List[ImageResponse]) 
async def get_all_images():
    db = SessionLocal()
    try:
        images = db.query(Image).all()  # Ambil semua gambar dari database
        return images  # Kembalikan daftar gambar
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving images: {str(e)}")
    finally:
        db.close()

@app.get("/show/")
async def show_image(filename: str):
    # Path file gambar
    file_path = os.path.join(IMAGEDIR, filename)

    # Cek file yang ada di direktori images
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


# from typing import Union

# from fastapi import FastAPI, File, UploadFile, HTTPException # type: ignore
# import uuid
# from fastapi.responses import FileResponse # type: ignore
# import os
# import pymysql # type: ignore
# from dotenv import load_dotenv # type: ignore

# load_dotenv('.env')

# db = pymysql.connect(
#     port=os.getenv('DB_PORT'),
#     host=os.getenv('DB_HOST'),
#     user=os.getenv('DB_USER'),
#     password=os.getenv('DB_PASSWORD'),
#     database=os.getenv('DB_DATABASE')
# )

# IMAGEDIR = "images/"

# app = FastAPI()

# @app.get('/')
# def read_root():
#     return{"Hello": "World"} 
 
# @app.post("/upload/")
# async def create_upload_file(file: UploadFile = File(...), device_id: str = "unknown"):
#     # buat nama file pake uuid
#     file.filename = f"{uuid.uuid4()}.jpg"
#     contents = await file.read()

#     # Simpan dir saya
#     file_path = os.path.join(IMAGEDIR, file.filename)
#     with open(file_path, "wb") as f:
#         f.write(contents)

#     # Simpan database
#     try:
#         cursor = db.cursor()
#         sql = "INSERT INTO images (filename, filepath, device_id) VALUES (%s, %s, %s)"
#         cursor.execute(sql, (file.filename, file_path, device_id))
#         db.commit()
#     except pymysql.MySQLError as e:
#         raise HTTPException(status_code=500, detail=f"Error saving image to database: {str(e)}")
#     finally:
#         cursor.close()

#     return {"filename": file.filename, "filepath": file_path}

# @app.get("/show/")
# async def show_image(filename: str):
#     # Path file gambar
#     file_path = os.path.join(IMAGEDIR, filename)

#     # Cek file yang ada di direktori imgaes
#     if not os.path.isfile(file_path):
#         raise HTTPException(status_code=404, detail="File not found")

#     return FileResponse(file_path)


# butuh python.env
# isi env ini
# import pymysql # type: ignore

# db = pymysql.connect(
#     host='localhost',
#     user='root',
#     password='',
#     database='apiiteba'
# )

# referensi pakai sqlachamey