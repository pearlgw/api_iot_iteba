import os
import requests # type: ignore
import uuid

# URL tujuan untuk POST request
url = 'http://103.124.196.178:8000/upload'

# Direktori tempat file statis berada
directory = 'images/'

# Looping melalui semua file di dalam direktori
for filename in os.listdir(directory):
    # Ambil path lengkap file
    file_path = os.path.join(directory, filename)
    
    # Pastikan hanya file, bukan folder
    if os.path.isfile(file_path):
        # Buka file untuk dikirim
        with open(file_path, 'rb') as f:
            # Membuat device_id secara random menggunakan uuid
            device_id = str(uuid.uuid4())

            # Menyiapkan data dalam format form-data
            files = {
                'file': (filename, f)  # Key untuk form-data, mengirim file
            }
            # Menyiapkan data tambahan untuk atribut lainnya
            data = {
                'device_id': device_id  # Menambahkan device_id secara random
            }

            # Mengirim POST request dengan file dan data
            response = requests.post(url, files=files, data=data)
            
            # Menampilkan respon dari server
            print(f"File {filename} uploaded with device_id {device_id}, response: {response.status_code}")
            print(f"Response content: {response.text}")
