// Renderer process for Manga Colorizer

let socket;
let serverUrl = 'http://localhost:5000';
let selectedFile = null;
let isProcessing = false;

// DOM Elements
const dropZone = document.getElementById('dropZone');
const browseBtn = document.getElementById('browseBtn');
const fileInfo = document.getElementById('fileInfo');
const startBtn = document.getElementById('startBtn');
const cancelBtn = document.getElementById('cancelBtn');
const progressSection = document.getElementById('progressSection');
const statusText = document.getElementById('statusText');
const progressText = document.getElementById('progressText');
const progressBar = document.getElementById('progressBar');
const resultsSection = document.getElementById('resultsSection');
const resultsGrid = document.getElementById('resultsGrid');

// Config elements
const promptInput = document.getElementById('promptInput');
const textProtectionCheck = document.getElementById('textProtectionCheck');
const colorConsistencyCheck = document.getElementById('colorConsistencyCheck');
const createZipCheck = document.getElementById('createZipCheck');

// Initialize
async function initialize() {
    setupSocketIO();
    setupEventListeners();
    
    // Check server status
    try {
        const response = await fetch(`${serverUrl}/api/status`);
        const data = await response.json();
        if (data.status === 'running') {
            statusText.textContent = 'Ready - Neural colorization loaded';
            console.log('Server is running');
        }
    } catch (error) {
        statusText.textContent = 'Waiting for server...';
        console.error('Server not ready:', error);
        setTimeout(initialize, 2000);
    }
}

// Setup Socket.IO connection
function setupSocketIO() {
    socket = io(serverUrl);

    socket.on('connect', () => {
        console.log('Connected to server');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });

    socket.on('progress', (data) => {
        updateProgress(data);
    });

    socket.on('status', (data) => {
        updateStatus(data.status, data.message);
    });

    socket.on('complete', (data) => {
        onComplete(data);
    });

    socket.on('error', (data) => {
        onError(data.error);
    });
}

// Setup event listeners
function setupEventListeners() {
    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    // Browse button
    browseBtn.addEventListener('click', async () => {
        const filePath = await window.electronAPI.selectFile();
        if (filePath) {
            // Create a File-like object from path
            handleFilePath(filePath);
        }
    });

    // Start button
    startBtn.addEventListener('click', startColorization);

    // Cancel button
    cancelBtn.addEventListener('click', cancelColorization);
}

// Update slider value displays

// Handle file selection
function handleFileSelect(file) {
    selectedFile = file;
    fileInfo.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
    startBtn.disabled = false;
    dropZone.classList.add('has-file');
}

// Handle file path (from dialog)
async function handleFilePath(filePath) {
    try {
        const response = await fetch(`file://${filePath}`);
        const blob = await response.blob();
        const fileName = filePath.split('/').pop();
        selectedFile = new File([blob], fileName);
        fileInfo.textContent = `Selected: ${fileName}`;
        startBtn.disabled = false;
        dropZone.classList.add('has-file');
    } catch (error) {
        console.error('Error loading file:', error);
        // Fallback: store just the path
        selectedFile = { path: filePath, name: filePath.split('/').pop() };
        fileInfo.textContent = `Selected: ${selectedFile.name}`;
        startBtn.disabled = false;
        dropZone.classList.add('has-file');
    }
}

// Start colorization
async function startColorization() {
    if (!selectedFile || isProcessing) return;

    isProcessing = true;
    startBtn.style.display = 'none';
    cancelBtn.style.display = 'inline-block';
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';

    try {
        // Prepare form data
        const formData = new FormData();
        
        if (selectedFile.path) {
            // Read file from path
            const response = await fetch(`file://${selectedFile.path}`);
            const blob = await response.blob();
            formData.append('file', blob, selectedFile.name);
        } else {
            formData.append('file', selectedFile);
        }
        
        formData.append('create_zip', createZipCheck.checked);

        // Send request
        updateStatus('uploading', 'Uploading file...');
        
        const response = await fetch(`${serverUrl}/api/colorize`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to start colorization');
        }

        updateStatus('processing', 'Processing...');

    } catch (error) {
        console.error('Error starting colorization:', error);
        onError(error.message);
    }
}

// Cancel colorization
async function cancelColorization() {
    try {
        await fetch(`${serverUrl}/api/cancel`, { method: 'POST' });
        resetUI();
    } catch (error) {
        console.error('Error cancelling:', error);
    }
}

// Update server configuration
async function updateServerConfig() {
    const config = {
        model_name: modelSelect.value,
        prompt: promptInput.value,
        negative_prompt: negativePromptInput.value,
        num_inference_steps: parseInt(stepsInput.value),
        guidance_scale: parseFloat(guidanceInput.value),
        // denoise_strength removed - not used in txt2img
        enable_text_detection: textProtectionCheck.checked
    };

    try {
        const response = await fetch(`${serverUrl}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();
        if (!data.success) {
            console.error('Failed to update config:', data.error);
        }
    } catch (error) {
        console.error('Error updating config:', error);
    }
}

// Update progress
function updateProgress(data) {
    const percent = data.percent || 0;
    progressBar.style.width = `${percent}%`;
    progressText.textContent = `Processing: ${data.filename} (${data.current}/${data.total})`;
}

// Update status
function updateStatus(status, message) {
    statusText.textContent = message || status;
    
    if (status === 'complete') {
        progressBar.style.width = '100%';
    }
}

// On completion
function onComplete(data) {
    isProcessing = false;
    updateStatus('complete', 'Colorization complete!');
    
    // Show results
    resultsSection.style.display = 'block';
    displayResults(data);
    
    resetUI();
}

// On error
function onError(error) {
    isProcessing = false;
    updateStatus('error', `Error: ${error}`);
    progressBar.style.width = '0%';
    resetUI();
}

// Display results
function displayResults(data) {
    resultsGrid.innerHTML = '';

    if (data.output_files && data.output_files.length > 0) {
        data.output_files.slice(0, 9).forEach(filePath => {
            const fileName = filePath.split('/').pop();
            const img = document.createElement('img');
            img.src = `${serverUrl}/api/output/${fileName}`;
            img.alt = fileName;
            img.className = 'result-image';
            resultsGrid.appendChild(img);
        });
    } else if (data.output_file) {
        const fileName = data.output_file.split('/').pop();
        const img = document.createElement('img');
        img.src = `${serverUrl}/api/output/${fileName}`;
        img.alt = fileName;
        img.className = 'result-image';
        resultsGrid.appendChild(img);
    }
}

// Reset UI
function resetUI() {
    startBtn.style.display = 'inline-block';
    cancelBtn.style.display = 'none';
    startBtn.disabled = selectedFile === null;
}

// Utility: Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Initialize on load
document.addEventListener('DOMContentLoaded', initialize);
