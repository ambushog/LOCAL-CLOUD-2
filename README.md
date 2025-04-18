# LOCAL-CLOUD-2

# 📁 Local Cloud Storage with FastAPI

A secure, admin-controlled, self-hosted cloud storage solution built with **FastAPI**. Upload, download, stream, share, and manage files easily through a simple and powerful web interface.

---

## 🚀 Features

- 🔒 **Admin Authentication** (HTTP Basic Auth)
- ⚙️ **First-time Setup UI** (Admin credentials, storage directory, quota)
- 📤 **Secure File Upload** (Single & Multiple)
- 📥 **Protected Download Access**
- 🔗 **Share Files via Temporary or Password-Protected Links**
- 🎞️ **Built-in Video Player**
- 🧹 **Background Cleanup for Expired Share Links**
- 📊 **Disk Usage Dashboard**
- 💾 **Storage Limit Enforcement**
- 🖥️ **Responsive Web Interface**

---

## 🧑‍💻 Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) – Web framework
- [Uvicorn](https://www.uvicorn.org/) – ASGI server
- [bcrypt](https://pypi.org/project/bcrypt/) – Secure password hashing
- [psutil](https://pypi.org/project/psutil/) – Disk usage and system monitoring
- Vanilla HTML/CSS + JS – No frontend frameworks!

---

## 🏗️ Setup Instructions

### ✅ Requirements

- Python 3.9+
- pip (Python package manager)

### 📦 Installation

```bash
git clone https://github.com/yourusername/local-cloud-storage.git
cd local-cloud-storage
pip install -r requirements.txt
```

> You can also use the included `start.sh` script to start the server if you're on Linux/Mac.

### 🖥️ Run the App

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 5107
```

Or simply:

```bash
bash start.sh
```

---

## 🔧 First-Time Setup

Visit [`http://localhost:5107/setup`]to:

- Create an admin account
- Set a storage directory
- Configure storage quota (in GB)

Once setup is complete, you will be redirected to the home page.

---

## 🔐 Admin Actions (Basic Auth Required)

All major file actions are protected and require HTTP Basic authentication.

### Upload a File
`POST /upload/`

### Upload Multiple Files
`POST /upload-multiple/`

### List Files
`GET /list/`

### Download File
`GET /download/{filename}`

### Delete File
`DELETE /delete/{filename}`

### Share File
`POST /share/{filename}`

Params:
- `validity`: expiry in seconds *(optional)*
- `password`: password to protect link *(optional)*

### Access Shared File
`GET /shared/{share_id}`

If password protected, user will see a password input form.

### Video Player
`GET /player/{filename}`

### Storage Info
`GET /storage-info`

### Update Storage Limit
`POST /update-storage-limit`

---

## 📂 File Structure

```text
.
├── app.py                  # Main FastAPI app
├── local_cloud_config.json # Auto-generated config
├── static/                 # Static files like index.html
├── start.sh                # Start script
└── README.md               # This file
```

---

## 📜 License

MIT License – You are free to use, modify, and distribute this project.

**STILL WORKING. WILL UPDATE MORE LATER!!**

✅ We will also provide **updates**, so stay tuned!


## 🧑‍💼 Author

Made with ❤️ by Navaura_Arctiq
