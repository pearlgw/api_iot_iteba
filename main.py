from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends # type: ignore
import uuid
from fastapi.responses import FileResponse # type: ignore
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean # type: ignore
from sqlalchemy.orm import sessionmaker, declarative_base, Session # type: ignore
from dotenv import load_dotenv # type: ignore
from pydantic import BaseModel # type: ignore
from datetime import datetime
import pytz # type: ignore
from datetime import timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
import cv2 # type: ignore
from ultralytics import YOLO  # type: ignore # Model YOLOv8

load_dotenv('.env')

# Setup database URL
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@" \
               f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_DATABASE')}"

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20, pool_recycle=3600, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model definition
class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(255), nullable=False)
    device_id = Column(String(255), nullable=False)
    upload_time = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    filename_labeled = Column(String(255), nullable=True)
    labeled_filepath = Column(String(255), nullable=True)
    count = Column(Integer, nullable=True)
    level = Column(String(50), nullable=True)       
    
# Model untuk API Key
class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))

    def __init__(self, api_key: str, expires_in_years: int = 1):
        self.api_key = api_key
        self.expires_at = datetime.now(pytz.timezone('Asia/Jakarta')) + timedelta(days=365 * expires_in_years) # type: ignore

# Model baru untuk tabel images_labeled
class ImageLabeled(Base):
    __tablename__ = "images_labeled"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String(255), nullable=False)  # Foreign key dari tabel images
    labeled_filename = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False)  # Level dari hasil labeling
    count = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))

# Model Pydantic untuk response
class ImageResponse(BaseModel):
    id: int  # Ubah ini menjadi string
    filename: str
    filepath: str
    device_id: str
    upload_time: datetime
    filename_labeled: str = None
    labeled_filepath: str = None
    count: int = None
    level: str = None      

    class Config:
        orm_mode = True

# Pydantic model untuk API Key response
class APIKeyResponse(BaseModel):
    api_key: str
    expires_at: datetime
    created_at: datetime

    class Config:
        orm_mode = True

# Pydantic model untuk response ImageLabeled
class ImageLabeledResponse(BaseModel):
    # id: int
    image_id: str
    labeled_filename: str
    level: str
    count: int
    timestamp: datetime

    class Config:
        orm_mode = True
        
IMAGEDIR = "images/"
# IMAGEDLABELEDDIR = "images_labeled/"
LABELED_FOLDER = 'labeled/'  # Menyimpan langsung di folder labeled
os.makedirs(LABELED_FOLDER, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Ganti dengan URL frontend Anda
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
def read_root():
    return {"message": "Hallo Selamat Datang di API IoT Iteba"} 

model = YOLO('best.pt')  # Inisialisasi model YOLO

CLASS_NAMES = ['baja', 'ban_karet', 'batu', 'botol_kaca', 'botol_minum_plastik', 'botol_plastik',
               'bungkus_kertas', 'bungkus_makan_sterofoam', 'bungkus_makanan_plastik', 'bungkus_plastik',
               'bungkus_rokok', 'daun', 'gelas_kertas', 'gelas_plastik', 'gelas_sterofoam', 'kaca',
               'kaleng', 'kantong_plastik', 'kardus', 'kayu', 'kertas', 'pipa', 'plastik_makanan',
               'sedotan', 'sendal', 'sendok_plastik', 'tissue', 'tutup_minum_plastik']

@app.post("/upload/")
async def create_upload_file(file: UploadFile = File(...), device_id: str = Form(...)):
    # Buat nama file pake uuid
    file.filename = f"{uuid.uuid4()}.jpg"
    contents = await file.read()

    # Simpan file di direktori IMAGEDIR
    file_path = os.path.join(IMAGEDIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Simpan ke database
    db = SessionLocal()
    try:
        new_image = Image(
            filename=file.filename,
            filepath=file_path,
            device_id=device_id,
            upload_time=datetime.now(pytz.timezone('Asia/Jakarta'))
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving image to database: {str(e)}")
    finally:
        db.close()

    # Setelah gambar disimpan, proses gambar dengan YOLO
    frame = cv2.imread(file_path)

    # Deteksi objek menggunakan YOLO
    results = model(frame)
    detections = results[0].boxes

    # Dictionary untuk menghitung jumlah per kelas
    class_count = {cls_name: 0 for cls_name in CLASS_NAMES}

    # Gambarkan kotak deteksi pada frame
    for box in detections:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = box.conf[0]  # Confidence score
        cls = int(box.cls[0])  # Kelas objek

        # Nama kelas berdasarkan indeks
        class_name = CLASS_NAMES[cls]

        # Hitung jumlah kelas yang terdeteksi
        class_count[class_name] += 1

        # Gambarkan bounding box dan label pada frame
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f'{class_name} ({conf:.2f})', (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # Simpan gambar yang sudah diberi label ke folder labeled
    labeled_filename = f'labeled_{new_image.id}.jpg'
    labeled_image_path = os.path.join(LABELED_FOLDER, labeled_filename)
    cv2.imwrite(labeled_image_path, frame)

    # Total jumlah objek yang terdeteksi
    total_count = sum(class_count.values())

    # Tentukan level berdasarkan jumlah deteksi (total_count)
    if total_count < 3:
        level = 'rendah'  # Rendah
    elif total_count < 6:
        level = 'sedang'  # Sedang
    else:
        level = 'tinggi'  # Parah

    # Update kolom tambahan ke database setelah YOLO memproses
    db = SessionLocal()
    try:
        # Ambil objek image yang sudah ada
        db_image = db.query(Image).filter(Image.id == new_image.id).first()

        # Update kolom filename_labeled, labeled_filepath, count, dan level
        db_image.filename_labeled = labeled_filename
        db_image.labeled_filepath = labeled_image_path
        db_image.count = total_count
        db_image.level = level

        # Simpan perubahan
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating image in database: {str(e)}")
    finally:
        db.close()

    # Kembalikan respons dalam format dictionary
    return {
        "id": str(new_image.id),  # Mengubah ID menjadi string
        "filename": file.filename,  # Nama file asli
        "filepath": file_path,  # Lokasi file asli di IMAGEDIR
        "device_id": device_id,
        "upload_time": new_image.upload_time,
        "filename_labeled": labeled_filename,
        "labeled_filepath": labeled_image_path,
        "count": total_count,
        "level": level,
    }

# @app.post("/upload/", response_model=ImageResponse)
# async def create_upload_file(file: UploadFile = File(...), device_id: str = Form(...)):
#     # Buat nama file pake uuid
#     file.filename = f"{uuid.uuid4()}.jpg"
#     contents = await file.read()

#     # Simpan file di direktori
#     file_path = os.path.join(IMAGEDIR, file.filename)
#     with open(file_path, "wb") as f:
#         f.write(contents)

#     # Simpan ke database
#     db = SessionLocal()
#     try:
#         new_image = Image(
#             id=str(uuid.uuid4()),  # Menghasilkan UUID sebagai string
#             filename=file.filename,
#             filepath=file_path,
#             device_id=device_id,
#             upload_time=datetime.now(pytz.timezone('Asia/Jakarta'))
#         )
#         db.add(new_image)
#         db.commit()
#         db.refresh(new_image)
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Error saving image to database: {str(e)}")
#     finally:
#         db.close()

#     return {
#         "id": new_image.id,
#         "filename": file.filename,
#         "filepath": file_path,
#         "device_id": device_id,
#         "upload_time": new_image.upload_time
#     }

# Inisialisasi HTTPBearer untuk mengambil token dari header
bearer_scheme = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials, db: Session):
    api_key = credentials.credentials  # Ambil API key dari header
    api_key_instance = db.query(APIKey).filter(APIKey.api_key == api_key).first()

    if not api_key_instance:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Ambil waktu sekarang dengan timezone Asia/Jakarta
    now = datetime.now(pytz.timezone('Asia/Jakarta'))

    # Cek apakah API key sudah expired
    if api_key_instance.expires_at.replace(tzinfo=pytz.timezone('Asia/Jakarta')) < now:
        raise HTTPException(status_code=403, detail="API key has expired")
    
    return api_key_instance


@app.get("/images/", response_model=List[ImageResponse])
async def get_all_images(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    db = SessionLocal()
    try:
        # Verifikasi API key
        verify_api_key(credentials, db)

        images = db.query(Image).all()  # Ambil semua gambar dari database

        # Pastikan semua upload_time memiliki timezone
        for image in images:
            image.upload_time = image.upload_time.replace(tzinfo=pytz.timezone('Asia/Jakarta'))
        
        return images  # Kembalikan daftar gambar
    except HTTPException as e:
        raise e
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

@app.post("/generate-api-key/", response_model=APIKeyResponse)
def generate_api_key():
    # Membuat sesi database
    db = SessionLocal()
    try:
        # Generate API key baru secara otomatis menggunakan UUID
        new_api_key = str(uuid.uuid4())
        api_key_instance = APIKey(api_key=new_api_key)

        # Simpan API key ke database
        db.add(api_key_instance)
        db.commit()
        db.refresh(api_key_instance)

        return {
            "api_key": api_key_instance.api_key,
            "expires_at": api_key_instance.expires_at,
            "created_at": api_key_instance.created_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating API key: {str(e)}")
    finally:
        db.close()

# @app.post("/images/label/", response_model=ImageLabeledResponse)
# async def label_image(
#     image_id: str = Form(...),  # Menggunakan Form untuk image_id
#     file: UploadFile = File(...),  # File upload untuk labeled_filename
#     level: str = Form(...),
#     count: int = Form(...),  # Menambahkan jumlah yang terdeteksi sebagai input
# ):
#     db = SessionLocal()
#     try:
#         # Buat nama file baru untuk labeled image dengan UUID
#         labeled_filename = f"{uuid.uuid4()}.jpg"
#         contents = await file.read()

#         # Simpan file labeled image di direktori
#         labeled_file_path = os.path.join(IMAGEDLABELEDDIR, labeled_filename)
#         if not os.path.exists(IMAGEDLABELEDDIR):
#             os.makedirs(IMAGEDLABELEDDIR)  # Buat direktori jika belum ada

#         with open(labeled_file_path, "wb") as f:
#             f.write(contents)

#         # Buat entri baru untuk tabel images_labeled
#         new_label = ImageLabeled(
#             image_id=image_id,
#             labeled_filename=labeled_filename,
#             level=level,
#             count=count,  # Menyimpan jumlah yang terdeteksi
#             timestamp=datetime.now(pytz.timezone('Asia/Jakarta'))
#         )
#         db.add(new_label)
#         db.commit()
#         db.refresh(new_label)

#         return new_label
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Error labeling image: {str(e)}")
#     finally:
#         db.close()
        
@app.get("/show-labeled-images/")
async def show_labeled_image(filename: str):
    # Path file gambar
    file_path = os.path.join(LABELED_FOLDER, filename)

    # Cek file yang ada di direktori images
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)