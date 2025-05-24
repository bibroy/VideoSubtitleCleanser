# Running VideoSubtitleCleanser

This guide explains how to run the VideoSubtitleCleanser application in different environments and configurations.

## Development Environment Setup

### Prerequisites
- Python 3.8 or higher
- FFmpeg installed on your system
- Git (for cloning the repository)
- Node.js and npm (for frontend development, optional)

### Setting Up Your Environment

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/VideoSubtitleCleanser.git
cd VideoSubtitleCleanser
```

#### 2. Create a Virtual Environment
```bash
python -m venv venv
```

#### 3. Activate the Virtual Environment

On Windows:
```bash
venv\Scripts\activate
```

On macOS/Linux:
```bash
source venv/bin/activate
```

#### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 5. Set Up Environment Variables (Optional)
Create a `.env` file in the project root directory:

```
# AWS Credentials (if using AWS services)
AWS_ACCESS_KEY=your_access_key
AWS_SECRET_KEY=your_secret_key
AWS_REGION=us-east-1

# Application Settings
DEBUG=True
ENVIRONMENT=development
```

#### 6. Create Required Directories
The application needs certain directories for file storage. These will be created automatically when you run the application, but you can create them manually if needed:

```bash
mkdir -p data/uploads data/processed data/videos data/status
```

### Running the Application

#### Running the Backend Server

Navigate to the backend directory:
```bash
cd backend
```

Start the FastAPI server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Options:
- `--reload`: Enables auto-reload on file changes (development only)
- `--host 0.0.0.0`: Makes the server accessible from other devices on the network
- `--port 8000`: Specifies the port to run on

#### Accessing the Application
- Web Interface: Open your browser and navigate to `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs` or `http://localhost:8000/redoc`

## Running in Production

For production deployments, follow these additional steps:

### 1. Configure for Production

Update the `.env` file:
```
DEBUG=False
ENVIRONMENT=production
```

### 2. Use a Production ASGI Server

Install Gunicorn:
```bash
pip install gunicorn
```

Run with Gunicorn:
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app
```

Options:
- `-w 4`: Number of worker processes (usually 2 * number of CPU cores + 1)
- `-k uvicorn.workers.UvicornWorker`: Worker class for ASGI applications

### 3. Set Up a Reverse Proxy

For production deployments, it's recommended to use a reverse proxy like Nginx:

Example Nginx configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/VideoSubtitleCleanser/static/;
    }

    location /frontend/ {
        alias /path/to/VideoSubtitleCleanser/frontend/;
    }
}
```

### 4. Process Management

Use a process manager like Supervisor to keep the application running:

Example Supervisor configuration:
```ini
[program:videosubtitlecleanser]
command=/path/to/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app
directory=/path/to/VideoSubtitleCleanser
user=your_user
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
```

## Running with Docker

### 1. Build the Docker Image
```bash
docker build -t videosubtitlecleanser .
```

### 2. Run the Container
```bash
docker run -p 8000:8000 -v $(pwd)/data:/app/data videosubtitlecleanser
```

Options:
- `-p 8000:8000`: Maps port 8000 on the host to port 8000 in the container
- `-v $(pwd)/data:/app/data`: Mounts the data directory as a volume

### 3. Docker Compose (Optional)

Create a `docker-compose.yml` file:
```yaml
version: '3'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DEBUG=False
      - AWS_ACCESS_KEY=${AWS_ACCESS_KEY}
      - AWS_SECRET_KEY=${AWS_SECRET_KEY}
      - AWS_REGION=${AWS_REGION}
```

Run with Docker Compose:
```bash
docker-compose up -d
```

## Command Line Interface

The application also provides a command-line interface for batch processing:

### Basic Usage

Process a subtitle file:
```bash
python cli.py process --input path/to/subtitle.vtt --output path/to/output.vtt --cleanse --grammar --position
```

Extract subtitles from a video:
```bash
python cli.py extract --input path/to/video.mp4 --output path/to/output.vtt --language eng
```

Translate subtitles:
```bash
python cli.py translate --input path/to/subtitle.vtt --output path/to/output.vtt --source auto --target es
```

Analyze subtitles:
```bash
python cli.py analyze --input path/to/subtitle.vtt
```

### CLI Options

Common options for all commands:
- `--input`: Path to the input file
- `--output`: Path for the output file
- `--verbose`: Enable verbose output

Process command options:
- `--cleanse`: Enable error cleansing
- `--grammar`: Enable grammar correction
- `--no-position`: Disable position optimization
- `--diarize`: Enable speaker diarization
- `--format`: Output format (default: vtt)

Extract command options:
- `--language`: Language code for extraction (default: eng)

Translate command options:
- `--source`: Source language (auto for auto-detect)
- `--target`: Target language code
- `--quality`: Translation quality (standard or premium)

## Troubleshooting

### Common Issues

1. **FFmpeg Not Found**
   - Ensure FFmpeg is installed and in your system PATH
   - On Windows: Add FFmpeg bin directory to your PATH environment variable
   - On Linux: Install with `sudo apt-get install ffmpeg` or equivalent

2. **Permission Denied for Data Directory**
   - Ensure the application has write permissions for the data directory
   - If using Docker, check that volume mounts are correct

3. **AWS Services Not Working**
   - Verify AWS credentials are correctly set in .env file
   - Check network connectivity to AWS services

4. **Server Won't Start**
   - Check for port conflicts (something else might be using port 8000)
   - Verify the virtual environment is activated
   - Check log files for specific error messages

### Logs

Log files can be found in:
- Development: Console output when running with `--reload`
- Production: System logs when running with Gunicorn/Supervisor

## Updating the Application

To update the application:

1. Pull the latest code:
```bash
git pull origin main
```

2. Update dependencies:
```bash
pip install -r requirements.txt
```

3. Restart the application

## Running Tests

Run the test suite:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=backend tests/
```

## Performance Tuning

- **Worker Processes**: Adjust the number of Gunicorn workers based on your server's CPU cores
- **File Size Limits**: Configure maximum file size limits in FastAPI and Nginx
- **Timeouts**: Set appropriate timeouts for long-running processes
