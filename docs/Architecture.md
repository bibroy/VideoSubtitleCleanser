# VideoSubtitleCleanser Architecture

This document outlines the architecture of the VideoSubtitleCleanser application, detailing its components, data flow, and design decisions.

## Architecture Overview

The VideoSubtitleCleanser follows a modern web application architecture with a clear separation between frontend and backend components. The architecture is designed to be scalable, maintainable, and extensible.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│    Frontend     │◄───┤    Backend      │◄───┤   AWS Services  │
│    (HTML/JS)    │    │    (FastAPI)    │    │   (AI/ML/Gen)   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │                 │
                        │    Storage      │
                        │  (File System)  │
                        │                 │
                        └─────────────────┘
```

## Core Components

### 1. Backend (Python/FastAPI)

The backend is the core of the application, handling all subtitle processing logic, file management, and API endpoints.

#### Key Components:

- **API Layer**: FastAPI framework providing RESTful endpoints
- **Services Layer**: Core business logic for subtitle processing
- **Data Layer**: File system operations and task status management

#### Key Modules:

- **Subtitle Service**: Handles subtitle file operations
- **Processing Service**: Core subtitle enhancement logic
- **Translation Service**: Manages subtitle translation
- **File Utils**: Utility functions for file operations

### 2. Frontend (HTML/JS/CSS)

The frontend provides a user-friendly interface for interacting with the application.

#### Key Components:

- **Upload Interface**: Drag-and-drop file upload for subtitles and videos
- **Processing Options**: UI for configuring subtitle enhancement options
- **Task Management**: Interface for tracking and managing processing tasks
- **Results Viewer**: Display of processed subtitles and analysis results

### 3. AI/ML Services Integration

The application leverages AWS AI/ML services for advanced subtitle processing features.

#### Integrated Services:

- **Grammar and Spelling Correction**: Language models for text correction
- **Speaker Diarization**: ML models to identify different speakers
- **Translation**: Neural machine translation services
- **Text Analysis**: NLP services for subtitle content analysis

## Data Flow

1. **File Upload**:
   - User uploads subtitle or video file via web UI
   - File is stored in the server's file system
   - A unique task ID is generated and associated with the file

2. **Processing**:
   - User selects processing options
   - Backend processes the subtitle file based on selected options
   - Processing status is tracked and updated

3. **AI/ML Processing**:
   - For advanced features, files are sent to appropriate AI/ML services
   - Results are received and integrated into the processed subtitle

4. **Result Delivery**:
   - Processed subtitle file is made available for download
   - Analysis results are displayed to the user

## Directory Structure

```
VideoSubtitleCleanser/
│
├── backend/                  # Backend application
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── models/              # Data models and schemas
│   ├── routers/             # API route definitions
│   │   ├── subtitle_router.py
│   │   ├── processing_router.py
│   │   └── translation_router.py
│   ├── services/            # Business logic services
│   │   ├── subtitle_service.py
│   │   ├── processing_service.py
│   │   └── translation_service.py
│   └── utils/               # Utility functions
│       └── file_utils.py
│
├── frontend/                # Frontend static files
│   ├── css/                # CSS stylesheets
│   ├── js/                 # JavaScript files
│   └── images/             # Image assets
│
├── data/                    # Data storage
│   ├── uploads/            # Uploaded subtitle and video files
│   ├── processed/          # Processed subtitle files
│   ├── videos/             # Uploaded video files
│   └── status/             # Task status information
│
├── templates/               # HTML templates
│   └── index.html          # Main application template
│
├── static/                  # Static files served by backend
│
├── tests/                   # Test files
│   └── test_processing.py  # Tests for processing functionality
│
└── docs/                    # Documentation
    ├── README.md
    ├── Architecture.md
    ├── Run.md
    └── Techstack.md
```

## API Endpoints

The application exposes the following RESTful API endpoints:

### Subtitle Endpoints

- `POST /api/subtitles/upload`: Upload a subtitle file
- `POST /api/subtitles/upload_video`: Upload a video file
- `GET /api/subtitles/status/{task_id}`: Get task status
- `GET /api/subtitles/download/{task_id}`: Download processed subtitle

### Processing Endpoints

- `POST /api/process/subtitle/{task_id}`: Process a subtitle file
- `POST /api/process/extract/{task_id}`: Extract subtitles from video
- `POST /api/process/analyze/{task_id}`: Analyze subtitle content
- `POST /api/process/cancel/{task_id}`: Cancel processing task

### Translation Endpoints

- `POST /api/translate/`: Translate subtitle content
- `GET /api/translate/languages`: List supported languages
- `GET /api/translate/detect/{task_id}`: Detect subtitle language

## Scalability Considerations

The architecture is designed with scalability in mind:

1. **Task Queue**: Processing tasks can be offloaded to a background task queue
2. **Stateless Backend**: The backend is designed to be stateless for horizontal scaling
3. **File Storage**: The file storage system can be replaced with cloud storage (S3)
4. **AI Service Integration**: AWS AI services scale automatically with demand

## Future Enhancements

The architecture allows for several future enhancements:

1. **User Authentication**: Add user accounts and authentication
2. **Cloud Storage**: Replace local file storage with cloud storage
3. **Task Queue**: Implement a dedicated task queue (e.g., Celery)
4. **Real-time Updates**: Add WebSocket support for real-time status updates
5. **Microservices**: Split functionality into dedicated microservices
