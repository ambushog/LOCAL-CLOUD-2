import os
import shutil
import time
import uuid
import json
import psutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, Request, Depends, status
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import List, Optional
from threading import Thread
from pydantic import BaseModel
import secrets
import bcrypt

# Constants
DEFAULT_CONFIG_FILE = "local_cloud_config.json"
DEFAULT_STORAGE_DIR = "local_cloud_storage"
DEFAULT_STORAGE_LIMIT = 3 * 1024 * 1024 * 1024  # 3GB in bytes
MAX_PERCENTAGE_OF_DISK = 0.9  # Maximum 90% of total disk space

# Global variables that will be set during setup
STORAGE_DIR = DEFAULT_STORAGE_DIR
STORAGE_LIMIT = DEFAULT_STORAGE_LIMIT
SETUP_COMPLETED = False
ADMIN_CREDENTIALS = {}

# Dictionary to store shareable links
SHARED_LINKS = {}

app = FastAPI()
security = HTTPBasic()

class StorageSettings(BaseModel):
    storage_limit_gb: float

class AdminSetup(BaseModel):
    admin_id: str
    admin_password: str
    storage_directory: str
    storage_limit_gb: float  # Add this field

def load_config():
    global STORAGE_DIR, STORAGE_LIMIT, SETUP_COMPLETED, ADMIN_CREDENTIALS
    if os.path.exists(DEFAULT_CONFIG_FILE):
        try:
            with open(DEFAULT_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                STORAGE_DIR = config.get('storage_directory', DEFAULT_STORAGE_DIR)
                STORAGE_LIMIT = config.get('storage_limit', DEFAULT_STORAGE_LIMIT)
                ADMIN_CREDENTIALS = config.get('admin_credentials', {})
                SETUP_COMPLETED = bool(ADMIN_CREDENTIALS)
                
                # Ensure storage directory exists
                if not os.path.exists(STORAGE_DIR):
                    os.makedirs(STORAGE_DIR)
                return True
        except Exception as e:
            print(f"Error loading config: {e}")
    return False

def save_config():
    config = {
        'storage_directory': STORAGE_DIR,
        'storage_limit': STORAGE_LIMIT,
        'admin_credentials': ADMIN_CREDENTIALS
    }
    with open(DEFAULT_CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if not SETUP_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Setup not completed. Please complete setup first.",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    admin_id = credentials.username
    if admin_id not in ADMIN_CREDENTIALS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    stored_password_hash = ADMIN_CREDENTIALS[admin_id]
    is_correct_password = bcrypt.checkpw(
        credentials.password.encode('utf-8'), 
        stored_password_hash.encode('utf-8')
    )
    
    if not is_correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return admin_id

def get_storage_size():
    total_size = 0
    for dirpath, _, filenames in os.walk(STORAGE_DIR):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def get_available_system_storage():
    disk = psutil.disk_usage('/')
    return {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "percent": disk.percent
    }

def format_size(size_bytes):
    """Format size in bytes to human-readable string"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

# Setup endpoint - accessible only before admin setup is completed
@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    if SETUP_COMPLETED:
        return RedirectResponse(url="/")
    
    system_storage = get_available_system_storage()
    max_possible_storage_gb = round((system_storage["total"] * MAX_PERCENTAGE_OF_DISK) / (1024**3), 2)
    
    setup_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Initial Setup - Local Cloud Storage</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .setup-container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                text-align: center;
                color: #333;
            }}
            .form-group {{
                margin-bottom: 15px;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }}
            input, button {{
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                box-sizing: border-box;
            }}
            button {{
                background-color: #4CAF50;
                color: white;
                border: none;
                cursor: pointer;
                font-size: 16px;
                margin-top: 10px;
            }}
            button:hover {{
                background-color: #45a049;
            }}
            .info-box {{
                background-color: #e7f3fe;
                border-left: 5px solid #2196F3;
                padding: 10px;
                margin-bottom: 15px;
            }}
        </style>
    </head>
    <body>
        <div class="setup-container">
            <h1>First-Time Setup</h1>
            <div class="info-box">
                <p>Welcome to Local Cloud Storage! Complete this setup to configure your storage settings and create admin credentials.</p>
                <p>Available disk space: {format_size(system_storage["free"])}</p>
                <p>Maximum recommended storage: {format_size(system_storage["total"] * MAX_PERCENTAGE_OF_DISK)}</p>
            </div>
            
            <form id="setupForm">
                <div class="form-group">
                    <label for="admin_id">Admin Username:</label>
                    <input type="text" id="admin_id" name="admin_id" required>
                </div>
                
                <div class="form-group">
                    <label for="admin_password">Admin Password:</label>
                    <input type="password" id="admin_password" name="admin_password" required>
                </div>
                
                <div class="form-group">
                    <label for="storage_directory">Storage Directory:</label>
                    <input type="text" id="storage_directory" name="storage_directory" 
                           value="{DEFAULT_STORAGE_DIR}" required>
                    <small>Leave as default or enter absolute path</small>
                </div>
                
                <div class="form-group">
                    <label for="storage_limit">Storage Limit (GB):</label>
                    <input type="number" id="storage_limit" name="storage_limit" 
                           value="3" min="1" max="{max_possible_storage_gb}" step="0.1" required>
                    <small>Maximum recommended: {max_possible_storage_gb} GB</small>
                </div>
                
                <button type="submit">Complete Setup</button>
            </form>
            <div id="message"></div>
        </div>
        
        <script>
            document.getElementById('setupForm').addEventListener('submit', function(e) {{
                e.preventDefault();
                
                const formData = {{
                    admin_id: document.getElementById('admin_id').value,
                    admin_password: document.getElementById('admin_password').value,
                    storage_directory: document.getElementById('storage_directory').value,
                    storage_limit_gb: parseFloat(document.getElementById('storage_limit').value)
                }};
                
                fetch('/complete-setup', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify(formData),
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        document.getElementById('message').innerHTML = 
                            '<p style="color: green;">Setup completed successfully! Redirecting...</p>';
                        setTimeout(() => {{
                            window.location.href = '/';
                        }}, 2000);
                    }} else {{
                        document.getElementById('message').innerHTML = 
                            `<p style="color: red;">Error: ${{data.detail}}</p>`;
                    }}
                }})
                .catch(error => {{
                    document.getElementById('message').innerHTML = 
                        `<p style="color: red;">Error: ${{error.message}}</p>`;
                }});
            }});
        </script>
    </body>
    </html>
    """
    return setup_html

@app.post("/complete-setup")
async def complete_setup(admin_setup: AdminSetup):
    global STORAGE_DIR, STORAGE_LIMIT, SETUP_COMPLETED, ADMIN_CREDENTIALS
    
    if SETUP_COMPLETED:
        raise HTTPException(status_code=400, detail="Setup already completed")
    
    # Validate storage directory
    if admin_setup.storage_directory:
        # Make absolute path if relative
        if not os.path.isabs(admin_setup.storage_directory):
            admin_setup.storage_directory = os.path.abspath(admin_setup.storage_directory)
        
        # Create directory if it doesn't exist
        try:
            if not os.path.exists(admin_setup.storage_directory):
                os.makedirs(admin_setup.storage_directory)
            # Check if directory is writable
            test_file = os.path.join(admin_setup.storage_directory, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            STORAGE_DIR = admin_setup.storage_directory
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid storage directory: {str(e)}")
    
    # Hash password
    password_hash = bcrypt.hashpw(admin_setup.admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Save admin credentials
    ADMIN_CREDENTIALS[admin_setup.admin_id] = password_hash
    
    # Update storage limit
    system_storage = get_available_system_storage()
    max_possible_storage = int(system_storage["total"] * MAX_PERCENTAGE_OF_DISK)
    requested_limit = int(admin_setup.storage_limit_gb * 1024 * 1024 * 1024)
    
    if requested_limit > max_possible_storage:
        raise HTTPException(status_code=400, detail=f"Requested storage limit exceeds maximum possible storage ({format_size(max_possible_storage)})")
    
    STORAGE_LIMIT = requested_limit
    SETUP_COMPLETED = True
    
    # Save configuration
    save_config()
    
    return {"success": True, "message": "Setup completed successfully"}

# Mount static files AFTER setup check
@app.on_event("startup")
async def startup_event():
    # Load configuration if exists
    load_config()
    
    if SETUP_COMPLETED:
        # Only mount static files if setup is completed
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Start cleanup thread
    Thread(target=cleanup_shared_links, daemon=True).start()

# Admin-protected endpoints
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), admin_id: str = Depends(verify_admin)):
    if get_storage_size() + file.size > STORAGE_LIMIT:
        raise HTTPException(status_code=400, detail="Storage limit exceeded")
    file_location = os.path.join(STORAGE_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "url": f"/download/{file.filename}"}

@app.get("/download/{filename}")
async def download_file(filename: str, admin_id: str = Depends(verify_admin)):
    file_path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)

@app.get("/list/")
def list_files(admin_id: str = Depends(verify_admin)):
    files = os.listdir(STORAGE_DIR)
    file_details = []
    for filename in files:
        file_path = os.path.join(STORAGE_DIR, filename)
        file_size = os.path.getsize(file_path)
        file_details.append({
            "filename": filename,
            "size": file_size,
            "size_human": format_size(file_size)
        })
    return {"files": file_details}

@app.delete("/delete/{filename}")
def delete_file(filename: str, admin_id: str = Depends(verify_admin)):
    file_path = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "File deleted successfully"}
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/upload-multiple/")
async def upload_multiple_files(files: List[UploadFile] = File(...), admin_id: str = Depends(verify_admin)):
    uploaded_files = []
    for file in files:
        if get_storage_size() + file.size > STORAGE_LIMIT:
            raise HTTPException(status_code=400, detail="Storage limit exceeded")
        file_location = os.path.join(STORAGE_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploaded_files.append({"filename": file.filename, "url": f"/download/{file.filename}"})
    return {"uploaded_files": uploaded_files}

@app.post("/share/{filename}")
def share_file(filename: str, validity: Optional[int] = Query(None), password: Optional[str] = Query(None), admin_id: str = Depends(verify_admin)):
    file_path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    share_id = str(uuid.uuid4())
    SHARED_LINKS[share_id] = {
        "filename": filename,
        "expires_at": time.time() + validity if validity else None,
        "password": password
    }
    return {"shareable_link": f"/shared/{share_id}"}


def cleanup_shared_links():
    while True:
        time.sleep(60)
        for share_id, data in list(SHARED_LINKS.items()):
            if data["expires_at"] and time.time() > data["expires_at"]:
                del SHARED_LINKS[share_id]


@app.get("/shared/{share_id}")
def access_shared_file(share_id: str, password: Optional[str] = Query(None)):
    if share_id not in SHARED_LINKS:
        raise HTTPException(status_code=404, detail="Shared link expired or not found")
    
    data = SHARED_LINKS[share_id]
    
    # Check if this is a password verification request via AJAX
    headers = {"Content-Type": "application/json"}
    if password is not None and data["password"]:
        if data["password"] == password:
            # Password is correct, we'll return the file below
            pass
        else:
            # Return JSON response for AJAX request indicating incorrect password
            return JSONResponse(
                status_code=403,
                headers=headers,
                content={"success": False, "message": "Incorrect password"}
            )
    
    # If password is required but not provided or we're showing the form initially
    if data["password"] and password is None:
        password_form = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Password Required</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .form-container {{
                    max-width: 400px;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h2 {{
                    text-align: center;
                    color: #333;
                    margin-top: 0;
                }}
                .form-group {{
                    margin-bottom: 15px;
                }}
                label {{
                    display: block;
                    margin-bottom: 5px;
                    font-weight: bold;
                }}
                input, button {{
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    box-sizing: border-box;
                }}
                button {{
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    cursor: pointer;
                    font-size: 16px;
                    margin-top: 10px;
                }}
                button:hover {{
                    background-color: #45a049;
                }}
                .error-message {{
                    color: #d32f2f;
                    background-color: #ffebee;
                    padding: 10px;
                    border-radius: 4px;
                    margin-bottom: 15px;
                    border-left: 4px solid #d32f2f;
                    display: none;
                }}
            </style>
        </head>
        <body>
            <div class="form-container">
                <h2>Password Required</h2>
                <p>This file is password protected. Please enter the password to access it.</p>
                <div id="error-message" class="error-message"></div>
                <form id="password-form">
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit">Access File</button>
                </form>
            </div>
            
            <script>
                document.getElementById('password-form').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    
                    const password = document.getElementById('password').value;
                    const errorMessage = document.getElementById('error-message');
                    
                    // Clear previous error message
                    errorMessage.style.display = 'none';
                    errorMessage.textContent = '';
                    
                    // Check if password is empty
                    if (!password) {{
                        errorMessage.textContent = 'Please enter a password';
                        errorMessage.style.display = 'block';
                        return;
                    }}
                    
                    // Send password to server
                    fetch(window.location.pathname + '?password=' + encodeURIComponent(password), {{
                        method: 'GET',
                        headers: {{
                            'Accept': 'application/json'
                        }}
                    }})
                    .then(response => {{
                        if (response.ok) {{
                            // Password is correct, download the file
                            window.location.href = window.location.pathname + '?password=' + encodeURIComponent(password);
                        }} else {{
                            return response.json().then(data => {{
                                throw new Error(data.message || 'Invalid password');
                            }});
                        }}
                    }})
                    .catch(error => {{
                        errorMessage.textContent = error.message;
                        errorMessage.style.display = 'block';
                    }});
                }});
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=password_form)
    
    # If we reach here, either no password is required or correct password was provided
    file_path = os.path.join(STORAGE_DIR, data["filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=data["filename"])



@app.get("/player/{filename}")
def media_player(filename: str, admin_id: str = Depends(verify_admin)):
    file_path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    media_html = f"""
    <html>
    <body>
        <video width='100%' controls>
            <source src='/download/{filename}' type='video/mp4'>
            Your browser does not support the video tag.
        </video>
    </body>
    </html>
    """
    return HTMLResponse(content=media_html)

@app.get("/storage-info")
def storage_info(admin_id: str = Depends(verify_admin)):
    system_storage = get_available_system_storage()
    app_storage = get_storage_size()
    max_possible_storage = int(system_storage["total"] * MAX_PERCENTAGE_OF_DISK)
    
    return {
        "system_storage": {
            "total": system_storage["total"],
            "used": system_storage["used"],
            "free": system_storage["free"],
            "percent": system_storage["percent"],
            "total_human": format_size(system_storage["total"]),
            "used_human": format_size(system_storage["used"]),
            "free_human": format_size(system_storage["free"])
        },
        "app_storage": {
            "used": app_storage,
            "limit": STORAGE_LIMIT,
            "used_human": format_size(app_storage),
            "limit_human": format_size(STORAGE_LIMIT)
        },
        "max_possible_storage": {
            "bytes": max_possible_storage,
            "human": format_size(max_possible_storage)
        }
    }

@app.post("/update-storage-limit")
def update_storage_limit(settings: StorageSettings, admin_id: str = Depends(verify_admin)):
    global STORAGE_LIMIT
    requested_limit = int(settings.storage_limit_gb * 1024 * 1024 * 1024)
    system_storage = get_available_system_storage()
    max_possible_storage = int(system_storage["total"] * MAX_PERCENTAGE_OF_DISK)
    
    if requested_limit > max_possible_storage:
        raise HTTPException(status_code=400, detail=f"Requested storage limit exceeds maximum possible storage ({format_size(max_possible_storage)})")
    
    STORAGE_LIMIT = requested_limit
    save_config()
    
    return {
        "message": "Storage limit updated successfully",
        "new_limit": STORAGE_LIMIT,
        "new_limit_human": format_size(STORAGE_LIMIT)
    }

@app.get("/")
def home(request: Request):
    if not SETUP_COMPLETED:
        return RedirectResponse(url="/setup")
    
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5107)    