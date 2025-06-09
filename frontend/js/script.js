// Main JavaScript for Video Subtitle Generator

// API endpoint configuration
const API_BASE_URL = 'http://localhost:5000/api';

// DOM Elements
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const browseButton = document.getElementById('browse-button');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const removeFileBtn = document.getElementById('remove-file');
const uploadContainer = document.getElementById('upload-container');
const optionsContainer = document.getElementById('options-container');
const progressContainer = document.getElementById('progress-container');
const resultContainer = document.getElementById('result-container');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const generateButton = document.getElementById('generate-button');
const downloadLink = document.getElementById('download-link');
const newSubtitleBtn = document.getElementById('new-subtitle');

// Form elements
const sourceLanguageSelect = document.getElementById('source-language');
const targetLanguageSelect = document.getElementById('target-language');
const toolSelect = document.getElementById('tool');
const diarizeCheckbox = document.getElementById('diarize');
const grammarCheckbox = document.getElementById('grammar');
const detectTextCheckbox = document.getElementById('detect-text');
const fontNameSelect = document.getElementById('font-name');
const fontSizeInput = document.getElementById('font-size');
const primaryColorInput = document.getElementById('primary-color');
const outlineColorInput = document.getElementById('outline-color');
const backColorInput = document.getElementById('back-color');
const primaryColorPicker = document.getElementById('primary-color-picker');
const outlineColorPicker = document.getElementById('outline-color-picker');
const backColorPicker = document.getElementById('back-color-picker');
const boldCheckbox = document.getElementById('bold');
const italicCheckbox = document.getElementById('italic');
const outlineInput = document.getElementById('outline');
const shadowInput = document.getElementById('shadow');

// Global variables
let uploadedFile = null;
let uploadedFileName = '';
let generatedFileName = '';

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Load available languages
    loadLanguages();
    
    // Check API health
    checkApiHealth();
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up color pickers
    setupColorPickers();
});

// Check if the API server is running
function checkApiHealth() {
    fetch(`${API_BASE_URL}/health`)
        .then(response => {
            if (!response.ok) {
                throw new Error('API server is not responding');
            }
            return response.json();
        })
        .then(data => {
            console.log('API server status:', data);
            
            // Check if Whisper is available
            if (!data.whisper_available) {
                const whisperOption = Array.from(toolSelect.options).find(option => option.value === 'whisper');
                if (whisperOption) {
                    whisperOption.disabled = true;
                    whisperOption.text += ' (Not Available)';
                }
                
                // If auto is selected and Whisper is not available, show a warning
                if (toolSelect.value === 'auto') {
                    console.warn('Whisper is not available. AWS will be used if configured, otherwise subtitle generation may fail.');
                }
            }
        })
        .catch(error => {
            console.error('Error checking API health:', error);
            alert('Error: API server is not running. Please start the server and refresh the page.');
        });
}

// Load available languages for transcription and translation
function loadLanguages() {
    fetch(`${API_BASE_URL}/languages`)
        .then(response => response.json())
        .then(data => {
            // Populate source language dropdown
            populateLanguageDropdown(sourceLanguageSelect, data.transcription_languages);
            
            // Populate target language dropdown
            populateLanguageDropdown(targetLanguageSelect, data.translation_languages, true);
        })
        .catch(error => {
            console.error('Error loading languages:', error);
        });
}

// Populate a language dropdown with options
function populateLanguageDropdown(selectElement, languages, includeEmptyOption = false) {
    // Check if this is the source language dropdown
    const isSourceLanguage = selectElement.id === 'source-language';
    
    // Clear existing options, but save Auto Detect option if it's the source language dropdown
    let autoDetectOption = null;
    if (isSourceLanguage) {
        // Find and save the Auto Detect option if it exists
        autoDetectOption = Array.from(selectElement.options).find(option => option.value === 'auto');
    }
    
    // Clear all options
    selectElement.innerHTML = '';
    
    // Re-add Auto Detect option for source language
    if (isSourceLanguage) {
        // If we found an existing Auto Detect option, use it; otherwise create a new one
        if (!autoDetectOption) {
            autoDetectOption = document.createElement('option');
            autoDetectOption.value = 'auto';
            autoDetectOption.textContent = 'Auto Detect';
        }
        selectElement.appendChild(autoDetectOption);
    }
    
    // Add empty option for target language
    if (includeEmptyOption) {
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = 'No Translation';
        selectElement.appendChild(emptyOption);
    }
    
    // Add language options
    Object.entries(languages).forEach(([code, name]) => {
        const option = document.createElement('option');
        option.value = code;
        option.textContent = name;
        selectElement.appendChild(option);
    });
}

// Set up event listeners
function setupEventListeners() {
    // File drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleFileDrop);
    
    // Browse button - only this button should trigger the file input
    browseButton.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Remove file button
    removeFileBtn.addEventListener('click', removeFile);
    
    // Generate button
    generateButton.addEventListener('click', handleGenerateSubtitle);
    
    // New subtitle button
    newSubtitleBtn.addEventListener('click', resetForm);
}

// Set up color pickers
function setupColorPickers() {
    // Convert ASS color format to HTML color format
    function assToHtmlColor(assColor) {
        // ASS format: &HAABBGGRR (AA = alpha, BB = blue, GG = green, RR = red)
        if (assColor.startsWith('&H')) {
            const colorValue = assColor.substring(2);
            if (colorValue.length === 8) {
                const alpha = colorValue.substring(0, 2);
                const blue = colorValue.substring(2, 4);
                const green = colorValue.substring(4, 6);
                const red = colorValue.substring(6, 8);
                return `#${red}${green}${blue}`;
            }
        }
        return '#FFFFFF'; // Default to white
    }
    
    // Convert HTML color format to ASS color format
    function htmlToAssColor(htmlColor, alpha = '00') {
        // HTML format: #RRGGBB
        if (htmlColor.startsWith('#')) {
            const red = htmlColor.substring(1, 3);
            const green = htmlColor.substring(3, 5);
            const blue = htmlColor.substring(5, 7);
            return `&H${alpha}${blue}${green}${red}`;
        }
        return '&H00FFFFFF'; // Default to white
    }
    
    // Set initial color picker values
    primaryColorPicker.value = assToHtmlColor(primaryColorInput.value);
    outlineColorPicker.value = assToHtmlColor(outlineColorInput.value);
    backColorPicker.value = assToHtmlColor(backColorInput.value);
    
    // Update ASS color input when color picker changes
    primaryColorPicker.addEventListener('input', () => {
        primaryColorInput.value = htmlToAssColor(primaryColorPicker.value);
    });
    
    outlineColorPicker.addEventListener('input', () => {
        outlineColorInput.value = htmlToAssColor(outlineColorPicker.value);
    });
    
    backColorPicker.addEventListener('input', () => {
        // Use 80 for semi-transparent background
        backColorInput.value = htmlToAssColor(backColorPicker.value, '80');
    });
    
    // Update color picker when ASS color input changes
    primaryColorInput.addEventListener('input', () => {
        primaryColorPicker.value = assToHtmlColor(primaryColorInput.value);
    });
    
    outlineColorInput.addEventListener('input', () => {
        outlineColorPicker.value = assToHtmlColor(outlineColorInput.value);
    });
    
    backColorInput.addEventListener('input', () => {
        backColorPicker.value = assToHtmlColor(backColorInput.value);
    });
}

// Handle drag over event
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.add('dragover');
}

// Handle drag leave event
function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');
}

// Handle file drop event
function handleFileDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove('dragover');
    
    if (e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        handleFile(file);
    }
}

// Handle file select event
function handleFileSelect(e) {
    // Prevent default behavior and stop propagation
    e.preventDefault();
    e.stopPropagation();
    
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        handleFile(file);
    }
}

// Handle file
function handleFile(file) {
    // Check if file is a video
    const validTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm'];
    if (!validTypes.includes(file.type)) {
        alert('Please select a valid video file (MP4, AVI, MOV, MKV, WEBM)');
        return;
    }
    
    // Store the file
    uploadedFile = file;
    uploadedFileName = file.name;
    
    // Display file info
    fileName.textContent = file.name;
    fileInfo.style.display = 'flex';
    
    // Hide upload area and show options
    uploadArea.style.display = 'none';
    optionsContainer.style.display = 'block';
    
    // Scroll to options
    optionsContainer.scrollIntoView({ behavior: 'smooth' });
}

// Remove file
function removeFile(e) {
    e.stopPropagation();
    
    // Clear file input
    fileInput.value = '';
    uploadedFile = null;
    uploadedFileName = '';
    
    // Hide file info
    fileInfo.style.display = 'none';
    
    // Hide options container
    optionsContainer.style.display = 'none';
}

// Handle generate subtitle button click
function handleGenerateSubtitle() {
    if (!uploadedFile) {
        alert('Please select a video file first');
        return;
    }
    
    // Show progress container
    uploadContainer.style.display = 'none';
    optionsContainer.style.display = 'none';
    progressContainer.style.display = 'block';
    
    // Upload the file first
    uploadFile()
        .then(uploadResponse => {
            // Update progress
            updateProgress(30, 'File uploaded. Generating subtitle...');
            
            // Generate subtitle
            return generateSubtitle(uploadResponse.filename);
        })
        .then(generateResponse => {
            // Update progress
            updateProgress(100, 'Subtitle generated successfully!');
            
            // Store generated filename
            generatedFileName = generateResponse.filename;
            
            // Show result container after a short delay
            setTimeout(() => {
                progressContainer.style.display = 'none';
                resultContainer.style.display = 'block';
                
                // Display the video filename in the result message
                document.getElementById('video-filename-display').textContent = uploadedFileName;
                
                // Set up direct download link - no JavaScript handling
                downloadLink.href = `/api/download/${generatedFileName}`;
                downloadLink.setAttribute('download', generatedFileName);
                
                // Make it look like a button but behave like a normal link
                downloadLink.onclick = null;
                
                // Log the download attempt to console
                downloadLink.addEventListener('click', function() {
                    console.log(`Download initiated for: ${generatedFileName}`);
                    // Add to download history if it doesn't already exist
                    if (!isFileInDownloadHistory(uploadedFileName, generatedFileName)) {
                        addToDownloadHistory(uploadedFileName, generatedFileName, 'Downloading...');
                        
                        // Update status after a delay
                        setTimeout(() => {
                            updateDownloadStatus(generatedFileName, 'Completed');
                        }, 3000);
                    }
                });
            }, 1000);
        })
        .catch(error => {
            console.error('Error:', error);
            alert(`Error: ${error.message || 'An error occurred during subtitle generation'}`);
            resetForm();
        });
}

// Upload file to server
function uploadFile() {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        
        fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to upload file');
                });
            }
            return response.json();
        })
        .then(data => {
            resolve(data);
        })
        .catch(error => {
            reject(error);
        });
    });
}

// Generate subtitle
function generateSubtitle(filename) {
    return new Promise((resolve, reject) => {
        // Get form values
        const sourceLanguage = sourceLanguageSelect.value;
        const targetLanguage = targetLanguageSelect.value;
        const tool = toolSelect.value;
        const diarize = diarizeCheckbox.checked;
        const grammar = grammarCheckbox.checked;
        const detectText = detectTextCheckbox.checked;
        const fontName = fontNameSelect.value;
        const fontSize = fontSizeInput.value;
        const primaryColor = primaryColorInput.value;
        const outlineColor = outlineColorInput.value;
        const backColor = backColorInput.value;
        const bold = boldCheckbox.checked ? 1 : 0;
        const italic = italicCheckbox.checked ? 1 : 0;
        const outline = outlineInput.value;
        const shadow = shadowInput.value;
        
        // Create request payload
        const payload = {
            filename,
            source_language: sourceLanguage,
            target_language: targetLanguage || null,
            tool,
            diarize,
            grammar,
            detect_text: detectText,
            font_name: fontName,
            font_size: fontSize,
            primary_color: primaryColor,
            outline_color: outlineColor,
            back_color: backColor,
            bold,
            italic,
            outline,
            shadow
        };
        
        // Debug language parameters
        console.log('DEBUG: Frontend - Language parameters:');
        console.log(`  Source language: ${sourceLanguage}`);
        console.log(`  Target language: ${targetLanguage || 'null'}`);
        console.log(`  Payload source_language: ${payload.source_language}`);
        console.log(`  Payload target_language: ${payload.target_language}`);
        
        // Add special handling for auto language detection
        if (sourceLanguage === 'auto') {
            console.log('Using automatic language detection');
            updateProgress(10, 'Detecting language automatically...');
        }
        
        console.log('DEBUG: Full payload:', payload);
        
        // Send request to generate subtitle
        fetch(`${API_BASE_URL}/generate-subtitle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to generate subtitle');
                });
            }
            return response.json();
        })
        .then(data => {
            resolve(data);
        })
        .catch(error => {
            reject(error);
        });
    });
}

// Update progress bar
function updateProgress(percent, message) {
    progressBar.style.width = `${percent}%`;
    progressText.textContent = message;
}

// Reset form
function resetForm() {
    // Clear file input
    fileInput.value = '';
    uploadedFile = null;
    uploadedFileName = '';
    
    // Hide containers
    fileInfo.style.display = 'none';
    optionsContainer.style.display = 'none';
    progressContainer.style.display = 'none';
    resultContainer.style.display = 'none';
    
    // Show upload container and upload area
    uploadContainer.style.display = 'block';
    uploadArea.style.display = 'block';
    
    // Reset progress bar
    progressBar.style.width = '0%';
    progressText.textContent = 'Uploading video file...';
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Function to check if a file is already in the download history
function isFileInDownloadHistory(videoFilename, subtitleFilename) {
    const historyContainer = document.getElementById('download-history');
    if (historyContainer) {
        const rows = document.querySelectorAll('#history-table-body .history-table-row');
        for (let i = 0; i < rows.length; i++) {
            const videoCell = rows[i].querySelector('.video-column');
            const subtitleCell = rows[i].querySelector('.subtitle-column');
            
            if (videoCell && subtitleCell && 
                videoCell.textContent === videoFilename && 
                subtitleCell.textContent === subtitleFilename) {
                return true;
            }
        }
    }
    return false;
}

// Function to initialize download history table
function initializeDownloadHistoryTable() {
    const historyContainer = document.getElementById('download-history');
    
    // Check if the table already exists
    const existingTable = document.querySelector('.history-table-container');
    if (existingTable) {
        // Table already exists, no need to recreate it
        return;
    }
    
    // Create a div-based table structure for better control
    const tableDiv = document.createElement('div');
    tableDiv.className = 'history-table-container';
    tableDiv.innerHTML = `
        <div class="history-table-header">
            <div class="history-table-row">
                <div class="history-table-cell header-cell video-column">Video File</div>
                <div class="history-table-cell header-cell subtitle-column">Subtitle File</div>
                <div class="history-table-cell header-cell status-column">Status</div>
            </div>
        </div>
        <div class="history-table-body" id="history-table-body">
            <!-- Rows will be added here -->
        </div>
    `;
    
    // Append the table to the container
    historyContainer.appendChild(tableDiv);
}

// Function to add to download history
function addToDownloadHistory(videoFilename, subtitleFilename, status) {
    // Initialize table if it doesn't exist
    initializeDownloadHistoryTable();
    
    // Create table row
    const tableBody = document.getElementById('history-table-body');
    if (tableBody) {
        const row = document.createElement('div');
        row.className = 'history-table-row';
        row.innerHTML = `
            <div class="history-table-cell video-column" data-label="Video File">${videoFilename}</div>
            <div class="history-table-cell subtitle-column" data-label="Subtitle File">${subtitleFilename}</div>
            <div class="history-table-cell status-column" data-label="Status" id="status-${subtitleFilename}">${status}</div>
        `;
        
        // Add to table body
        tableBody.appendChild(row);
    }
}

// Function to update download status
function updateDownloadStatus(filename, status) {
    const statusElement = document.getElementById(`status-${filename}`);
    if (statusElement) {
        statusElement.textContent = status;
        statusElement.style.color = status === 'Completed' ? 'var(--success-color)' : 'var(--primary-color)';
    }
}
