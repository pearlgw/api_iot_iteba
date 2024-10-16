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