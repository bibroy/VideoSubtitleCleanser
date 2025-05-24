// Global variables
let currentTaskId = null;
let currentFileName = null;
let uploadedFileType = null; // 'subtitle' or 'video'
let tasksList = [];

// DOM elements
document.addEventListener('DOMContentLoaded', function() {
    // Tab navigation
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            // Add active class to the clicked button
            btn.classList.add('active');
            
            // Hide all tab panes
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Show the selected tab pane
            const tabId = btn.dataset.tab;
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Toggle diarization options visibility
    const diarizeCheckbox = document.getElementById('option-diarize');
    diarizeCheckbox.addEventListener('change', function() {
        const diarizeOptions = document.querySelectorAll('.diarize-options');
        diarizeOptions.forEach(option => {
            option.style.display = this.checked ? 'flex' : 'none';
        });
    });
    
    // Upload functionality
    setupUploadHandlers();
    
    // Process button
    const processBtn = document.getElementById('btn-process');
    processBtn.addEventListener('click', () => {
        if (currentTaskId) {
            processSubtitle(currentTaskId);
        }
    });
    
    // Translate button
    const translateBtn = document.getElementById('btn-translate');
    translateBtn.addEventListener('click', () => {
        if (currentTaskId) {
            translateSubtitle(currentTaskId);
        }
    });
    
    // Analyze button
    const analyzeBtn = document.getElementById('btn-analyze');
    analyzeBtn.addEventListener('click', () => {
        if (currentTaskId) {
            analyzeSubtitle(currentTaskId);
        }
    });
    
    // Close notification
    const closeNotification = document.querySelector('.close-notification');
    closeNotification.addEventListener('click', () => {
        document.getElementById('task-notification').style.display = 'none';
    });

    // Poll for task status updates
    setInterval(updateTasksStatus, 5000);
});

// Setup upload handlers
function setupUploadHandlers() {
    const subtitleUploadBox = document.getElementById('upload-subtitle');
    const videoUploadBox = document.getElementById('upload-video');
    const subtitleInput = document.getElementById('subtitle-file-input');
    const videoInput = document.getElementById('video-file-input');
    
    // Subtitle upload via click
    subtitleUploadBox.addEventListener('click', () => {
        subtitleInput.click();
    });
    
    // Video upload via click
    videoUploadBox.addEventListener('click', () => {
        videoInput.click();
    });
    
    // Subtitle file selection
    subtitleInput.addEventListener('change', () => {
        if (subtitleInput.files.length > 0) {
            uploadFile(subtitleInput.files[0], 'subtitle');
        }
    });
    
    // Video file selection
    videoInput.addEventListener('change', () => {
        if (videoInput.files.length > 0) {
            uploadFile(videoInput.files[0], 'video');
        }
    });
    
    // Drag and drop for subtitle box
    setupDragDrop(subtitleUploadBox, (file) => uploadFile(file, 'subtitle'));
    
    // Drag and drop for video box
    setupDragDrop(videoUploadBox, (file) => uploadFile(file, 'video'));
}

// Setup drag and drop
function setupDragDrop(element, callback) {
    // Prevent default behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        element.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        element.addEventListener(eventName, () => {
            element.classList.add('highlight');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        element.addEventListener(eventName, () => {
            element.classList.remove('highlight');
        });
    });
    
    // Handle dropped files
    element.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        callback(file);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
}

// Upload file to server
async function uploadFile(file, type) {
    // Validate file type
    if (type === 'subtitle') {
        const validExtensions = ['.srt', '.vtt', '.sub', '.sbv', '.smi', '.ssa', '.ass'];
        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        
        if (!validExtensions.includes(ext)) {
            showNotification('error', 'Invalid subtitle file format. Please upload a supported format.');
            return;
        }
    } else if (type === 'video') {
        const validExtensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv'];
        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        
        if (!validExtensions.includes(ext)) {
            showNotification('error', 'Invalid video file format. Please upload a supported format.');
            return;
        }
    }
    
    // Show progress bar
    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.querySelector('.progress-fill');
    const progressPercent = document.querySelector('.progress-percent');
    progressDiv.style.display = 'block';
    
    try {
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        
        // Upload to appropriate endpoint
        const endpoint = type === 'subtitle' ? '/api/subtitles/upload' : '/api/subtitles/upload_video';
        
        // Upload with progress tracking
        const response = await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = `${percent}%`;
                    progressPercent.textContent = `${percent}%`;
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    reject(new Error(`Upload failed with status ${xhr.status}`));
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Network error occurred during upload'));
            });
            
            xhr.open('POST', endpoint);
            xhr.send(formData);
        });
        
        // Hide progress after successful upload
        progressDiv.style.display = 'none';
        
        // Store task info
        currentTaskId = response.task_id;
        currentFileName = file.name;
        uploadedFileType = type;
        
        // Add to tasks list
        addTaskToList(response);
        
        // Enable buttons
        document.getElementById('btn-process').disabled = false;
        document.getElementById('btn-translate').disabled = false;
        document.getElementById('btn-analyze').disabled = false;
        
        showNotification('success', `${file.name} uploaded successfully.`);
        
        // Switch to the process tab
        document.querySelector('.tab-btn[data-tab="process"]').click();
        
    } catch (error) {
        progressDiv.style.display = 'none';
        showNotification('error', `Upload failed: ${error.message}`);
    }
}

// Process subtitle with selected options
async function processSubtitle(taskId) {
    try {
        // Get options from the form        const options = {
            cleanse_errors: document.getElementById('option-cleanse').checked,
            correct_grammar: document.getElementById('option-grammar').checked,
            remove_invalid_chars: document.getElementById('option-chars').checked,
            correct_timing: document.getElementById('option-timing').checked,
            optimize_position: document.getElementById('option-position').checked,
            enforce_font_consistency: document.getElementById('option-fonts').checked,
            remove_duplicate_lines: document.getElementById('option-duplicates').checked,
            diarize_speakers: document.getElementById('option-diarize').checked,
            use_aws_transcribe: document.getElementById('option-use-aws').checked,
            max_speakers: parseInt(document.getElementById('max-speakers').value || 10),
            output_format: document.getElementById('output-format').value
        };
        
        // Send request to the API
        const response = await fetch(`/api/process/subtitle/${taskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(options)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('processing', 'Processing started. You will be notified when it completes.');
            
            // Switch to the tasks tab
            document.querySelector('.tab-btn[data-tab="tasks"]').click();
            
            // Update the task in the list
            updateTaskInList(data);
        } else {
            showNotification('error', `Processing request failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (error) {
        showNotification('error', `Processing request failed: ${error.message}`);
    }
}

// Translate subtitle
async function translateSubtitle(taskId) {
    try {
        // Get translation options
        const translationOptions = {
            task_id: taskId,
            source_language: document.getElementById('source-language').value === 'auto' ? null : document.getElementById('source-language').value,
            target_language: document.getElementById('target-language').value,
            preserve_formatting: document.getElementById('preserve-formatting').checked,
            quality: document.getElementById('translation-quality').value
        };
        
        // Send request to the API
        const response = await fetch('/api/translate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(translationOptions)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('processing', 'Translation started. You will be notified when it completes.');
            
            // Switch to the tasks tab
            document.querySelector('.tab-btn[data-tab="tasks"]').click();
            
            // Update the task in the list
            updateTaskInList(data);
        } else {
            showNotification('error', `Translation request failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (error) {
        showNotification('error', `Translation request failed: ${error.message}`);
    }
}

// Analyze subtitle
async function analyzeSubtitle(taskId) {
    try {
        // Send request to the API
        const response = await fetch(`/api/process/analyze/${taskId}`);
        const data = await response.json();
        
        if (response.ok) {
            displayAnalysisResults(data.analysis);
            showNotification('info', 'Analysis complete.');
        } else {
            showNotification('error', `Analysis failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (error) {
        showNotification('error', `Analysis failed: ${error.message}`);
    }
}

// Display analysis results
function displayAnalysisResults(analysis) {
    // Show the results section
    const resultsDiv = document.querySelector('.analysis-results');
    resultsDiv.style.display = 'block';
    
    // Statistics
    const statsContainer = document.getElementById('statistics-container');
    statsContainer.innerHTML = '';
    
    if (analysis.statistics) {
        for (const [key, value] of Object.entries(analysis.statistics)) {
            const statItem = document.createElement('div');
            statItem.className = 'statistic-item';
            
            const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            
            statItem.innerHTML = `
                <div class="statistic-value">${value}</div>
                <div class="statistic-label">${formattedKey}</div>
            `;
            
            statsContainer.appendChild(statItem);
        }
    }
    
    // Issues
    const issuesContainer = document.getElementById('issues-container');
    issuesContainer.innerHTML = '';
    
    if (analysis.issues && analysis.issues.length > 0) {
        analysis.issues.forEach(issue => {
            const issueItem = document.createElement('div');
            issueItem.className = `issue-item severity-${issue.severity || 'medium'}`;
            
            let title = '';
            let description = '';
            
            switch (issue.type) {
                case 'timing_overlap':
                    title = 'Timing Overlap';
                    description = `Subtitle ${issue.subtitle_index + 1} overlaps with the next subtitle.`;
                    break;
                case 'invalid_characters':
                    title = 'Invalid Characters';
                    description = `Found ${issue.count} subtitles with potentially invalid characters.`;
                    break;
                case 'grammar':
                    title = 'Grammar Issues';
                    description = `Found ${issue.count} subtitles with potential grammar issues.`;
                    break;
                default:
                    title = issue.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    description = `Issue affects ${issue.count || 'some'} subtitles.`;
            }
            
            issueItem.innerHTML = `
                <div class="issue-title">${title}</div>
                <div class="issue-description">${description}</div>
            `;
            
            issuesContainer.appendChild(issueItem);
        });
    } else {
        issuesContainer.innerHTML = '<p>No issues detected.</p>';
    }
    
    // Recommendations
    const recsContainer = document.getElementById('recommendations-container');
    recsContainer.innerHTML = '';
    
    if (analysis.recommendations && analysis.recommendations.length > 0) {
        analysis.recommendations.forEach(rec => {
            const recItem = document.createElement('div');
            recItem.className = 'recommendation-item';
            
            recItem.innerHTML = `<div>${rec.message}</div>`;
            
            recsContainer.appendChild(recItem);
        });
    } else {
        recsContainer.innerHTML = '<p>No recommendations available.</p>';
    }
}

// Add task to the tasks list
function addTaskToList(task) {
    // Add to our internal tasks array
    tasksList.push({
        task_id: task.task_id,
        filename: task.filename,
        status: task.status,
        upload_time: task.upload_time
    });
    
    // Update the UI
    updateTasksListUI();
}

// Update task in the list
function updateTaskInList(task) {
    // Find and update the task
    const index = tasksList.findIndex(t => t.task_id === task.task_id);
    
    if (index !== -1) {
        tasksList[index] = {
            ...tasksList[index],
            ...task
        };
    } else {
        // If not found, add it
        addTaskToList(task);
    }
    
    // Update the UI
    updateTasksListUI();
}

// Update the tasks list UI
function updateTasksListUI() {
    const tasksContainer = document.getElementById('tasks-list');
    
    if (tasksList.length === 0) {
        tasksContainer.innerHTML = '<div class="empty-tasks">No tasks yet</div>';
        return;
    }
    
    // Sort tasks by upload time (newest first)
    tasksList.sort((a, b) => {
        return new Date(b.upload_time) - new Date(a.upload_time);
    });
    
    tasksContainer.innerHTML = '';
    
    tasksList.forEach(task => {
        const taskItem = document.createElement('div');
        taskItem.className = 'task-item';
        taskItem.dataset.taskId = task.task_id;
        
        // Format status
        let statusClass, statusLabel;
        switch (task.status) {
            case 'uploaded':
                statusClass = 'status-uploaded';
                statusLabel = 'Uploaded';
                break;
            case 'processing':
            case 'extracting':
            case 'translating':
                statusClass = 'status-processing';
                statusLabel = 'Processing';
                break;
            case 'completed':
                statusClass = 'status-completed';
                statusLabel = 'Completed';
                break;
            case 'error':
                statusClass = 'status-error';
                statusLabel = 'Error';
                break;
            default:
                statusClass = 'status-uploaded';
                statusLabel = task.status;
        }
        
        taskItem.innerHTML = `
            <div class="task-status">
                <span class="status-badge ${statusClass}">${statusLabel}</span>
            </div>
            <div class="task-details">
                <div class="task-title">${task.filename || 'Unnamed Task'}</div>
                <div class="task-info">Task ID: ${task.task_id}</div>
                ${task.progress ? `<div class="task-progress">Progress: ${task.progress}%</div>` : ''}
            </div>
            <div class="task-actions">
                ${task.status === 'completed' ? `
                    <button class="btn-icon download-task" title="Download" data-task-id="${task.task_id}">
                        <i class="fas fa-download"></i>
                    </button>
                ` : ''}
                <button class="btn-icon select-task" title="Select" data-task-id="${task.task_id}">
                    <i class="fas fa-check-circle"></i>
                </button>
            </div>
        `;
        
        tasksContainer.appendChild(taskItem);
    });
    
    // Add event listeners to the action buttons
    document.querySelectorAll('.download-task').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const taskId = e.currentTarget.dataset.taskId;
            downloadProcessedSubtitle(taskId);
        });
    });
    
    document.querySelectorAll('.select-task').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const taskId = e.currentTarget.dataset.taskId;
            const task = tasksList.find(t => t.task_id === taskId);
            if (task) {
                currentTaskId = task.task_id;
                currentFileName = task.filename;
                
                // Enable buttons
                document.getElementById('btn-process').disabled = false;
                document.getElementById('btn-translate').disabled = false;
                document.getElementById('btn-analyze').disabled = false;
                
                showNotification('info', `Selected task: ${task.filename || task.task_id}`);
            }
        });
    });
}

// Download processed subtitle
function downloadProcessedSubtitle(taskId) {
    window.location.href = `/api/subtitles/download/${taskId}`;
}

// Periodically update tasks status
async function updateTasksStatus() {
    try {
        // For each task that is in progress, check its status
        const processingTasks = tasksList.filter(task => 
            task.status === 'processing' || 
            task.status === 'extracting' || 
            task.status === 'translating'
        );
        
        for (const task of processingTasks) {
            const response = await fetch(`/api/subtitles/status/${task.task_id}`);
            const updatedTask = await response.json();
            
            // If status changed
            if (updatedTask.status !== task.status) {
                // Update in our list
                updateTaskInList(updatedTask);
                
                // Show notification if completed or error
                if (updatedTask.status === 'completed') {
                    showNotification('success', `Task ${updatedTask.task_id} completed successfully!`);
                } else if (updatedTask.status === 'error') {
                    showNotification('error', `Task ${updatedTask.task_id} failed: ${updatedTask.error_message || 'Unknown error'}`);
                }
            }
        }
    } catch (error) {
        console.error('Error updating task statuses:', error);
    }
}

// Show notification
function showNotification(type, message) {
    const notification = document.getElementById('task-notification');
    const icon = notification.querySelector('.task-icon');
    const messageElement = notification.querySelector('.task-message');
    
    // Set icon based on notification type
    switch (type) {
        case 'success':
            icon.className = 'task-icon fas fa-check-circle';
            icon.style.color = 'var(--success-color)';
            break;
        case 'error':
            icon.className = 'task-icon fas fa-exclamation-circle';
            icon.style.color = 'var(--danger-color)';
            break;
        case 'processing':
            icon.className = 'task-icon fas fa-spinner fa-spin';
            icon.style.color = 'var(--info-color)';
            break;
        case 'info':
        default:
            icon.className = 'task-icon fas fa-info-circle';
            icon.style.color = 'var(--primary-color)';
            break;
    }
    
    // Set message
    messageElement.textContent = message;
    
    // Show notification
    notification.style.display = 'flex';
    
    // Auto-hide after 5 seconds for success and info
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);
    }
}
