// state
let currentFileId = null;
let pollingInterval = null;
let currentTranscript = null;

// DOM elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const statusSection = document.getElementById('status-section');
const resultsSection = document.getElementById('results-section');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const statusBadge = document.getElementById('status-badge');
const fileName = document.getElementById('file-name');
const errorSection = document.getElementById('error-section');
const errorMessage = document.getElementById('error-message');
const newUploadBtn = document.getElementById('new-upload-btn');

// step elements
const stepUpload = document.getElementById('step-upload');
const stepTranscribe = document.getElementById('step-transcribe');
const stepSummarize = document.getElementById('step-summarize');

// drag and drop handlers
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

uploadZone.addEventListener('click', () => {
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// main upload handler
async function handleFile(file) {
    // validate file type
    const validTypes = ['.mp3', '.mp4', '.wav', '.m4a', '.webm', '.ogg', '.mpeg', '.aac'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validTypes.includes(ext)) {
        alert('Unsupported file type. Please upload an audio or video file.');
        return;
    }

    // show status section
    uploadZone.classList.add('hidden');
    statusSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    newUploadBtn.classList.add('hidden');

    // reset steps
    resetSteps();
    stepUpload.classList.add('active');

    fileName.textContent = file.name;
    updateStatus('pending', 'Uploading...');
    updateProgress(0);

    try {
        // upload file
        const formData = new FormData();
        formData.append('file', file);

        updateProgress(10);
        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const uploadData = await uploadResponse.json();
        currentFileId = uploadData.file_id;

        stepUpload.classList.remove('active');
        stepUpload.classList.add('done');
        updateProgress(20);

        // start transcription
        stepTranscribe.classList.add('active');
        updateStatus('processing', 'Starting transcription...');

        const transcribeResponse = await fetch(`/api/transcribe/${currentFileId}`, {
            method: 'POST'
        });

        if (!transcribeResponse.ok) {
            const error = await transcribeResponse.json();
            throw new Error(error.detail || 'Failed to start transcription');
        }

        // poll for transcription status
        await pollTranscriptionStatus();

    } catch (error) {
        showError(error.message);
    }
}

// poll transcription status
async function pollTranscriptionStatus() {
    return new Promise((resolve, reject) => {
        pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/transcribe/${currentFileId}/status`);
                const data = await response.json();

                if (data.status === 'processing') {
                    const progress = 20 + (data.progress * 0.4); // 20-60%
                    updateProgress(progress);
                    updateStatus('processing', `Transcribing... ${data.progress}%`);
                }
                else if (data.status === 'completed') {
                    clearInterval(pollingInterval);
                    currentTranscript = data.transcript;

                    stepTranscribe.classList.remove('active');
                    stepTranscribe.classList.add('done');
                    updateProgress(60);

                    // start summarization
                    await startSummarization();
                    resolve();
                }
                else if (data.status === 'failed') {
                    clearInterval(pollingInterval);
                    reject(new Error(data.error || 'Transcription failed'));
                }
            } catch (error) {
                clearInterval(pollingInterval);
                reject(error);
            }
        }, 2000);
    });
}

// start summarization
async function startSummarization() {
    stepSummarize.classList.add('active');
    updateStatus('processing', 'Generating summary...');
    updateProgress(65);

    try {
        const response = await fetch(`/api/summarize/${currentFileId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start summarization');
        }

        // poll for summary status
        await pollSummaryStatus();

    } catch (error) {
        showError(error.message);
    }
}

// poll summary status
async function pollSummaryStatus() {
    return new Promise((resolve, reject) => {
        pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/summarize/${currentFileId}/status`);
                const data = await response.json();

                if (data.status === 'processing') {
                    updateProgress(70);
                    updateStatus('processing', 'Analyzing with AI...');
                }
                else if (data.status === 'completed') {
                    clearInterval(pollingInterval);

                    stepSummarize.classList.remove('active');
                    stepSummarize.classList.add('done');
                    updateProgress(100);
                    updateStatus('completed', 'Done!');

                    // display results
                    displayResults(data);
                    newUploadBtn.classList.remove('hidden');
                    resolve();
                }
                else if (data.status === 'failed') {
                    clearInterval(pollingInterval);
                    reject(new Error(data.error || 'Summarization failed'));
                }
            } catch (error) {
                clearInterval(pollingInterval);
                reject(error);
            }
        }, 2000);
    });
}

// display results
function displayResults(data) {
    resultsSection.classList.remove('hidden');

    // summary
    const summaryList = document.getElementById('summary-list');
    summaryList.innerHTML = data.summary.map(item => `<li>${item}</li>`).join('');

    // action items
    const actionsList = document.getElementById('actions-list');
    actionsList.innerHTML = data.action_items.map(item => `
        <li class="action-item">
            <span class="action-task">${item.task}</span>
            ${item.owner ? `<span class="action-owner">${item.owner}</span>` : ''}
        </li>
    `).join('');

    // key decisions
    const decisionsList = document.getElementById('decisions-list');
    decisionsList.innerHTML = data.key_decisions.map(item => `<li>${item}</li>`).join('');

    // follow-up questions
    const questionsList = document.getElementById('questions-list');
    questionsList.innerHTML = data.follow_up_questions.map(item => `<li>${item}</li>`).join('');

    // transcript
    document.getElementById('transcript-content').textContent = currentTranscript || 'Transcript not available';
}

// update UI helpers
function updateProgress(percent) {
    progressFill.style.width = `${percent}%`;
}

function updateStatus(status, text) {
    statusBadge.className = `status-badge ${status}`;
    statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    progressText.textContent = text;
}

function resetSteps() {
    [stepUpload, stepTranscribe, stepSummarize].forEach(step => {
        step.classList.remove('active', 'done');
    });
}

function showError(message) {
    updateStatus('failed', 'Error');
    errorSection.classList.remove('hidden');
    errorMessage.textContent = message;
    newUploadBtn.classList.remove('hidden');

    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
}

function resetUpload() {
    uploadZone.classList.remove('hidden');
    statusSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    currentFileId = null;
    currentTranscript = null;
    fileInput.value = '';
    resetSteps();
}

// copy functionality
function copySection(elementId) {
    const element = document.getElementById(elementId);
    let text = '';

    if (element.tagName === 'UL') {
        const items = element.querySelectorAll('li');
        text = Array.from(items).map(li => {
            const task = li.querySelector('.action-task');
            const owner = li.querySelector('.action-owner');
            if (task) {
                return owner ? `- ${task.textContent} (${owner.textContent})` : `- ${task.textContent}`;
            }
            return `- ${li.textContent}`;
        }).join('\n');
    } else {
        text = element.textContent;
    }

    copyToClipboard(text, event.target);
}

function copyAll() {
    const summary = document.getElementById('summary-list');
    const actions = document.getElementById('actions-list');
    const decisions = document.getElementById('decisions-list');
    const questions = document.getElementById('questions-list');

    let text = '# Meeting Notes\n\n';
    text += '## Summary\n' + getListText(summary) + '\n\n';
    text += '## Action Items\n' + getListText(actions) + '\n\n';
    text += '## Key Decisions\n' + getListText(decisions) + '\n\n';
    text += '## Follow-up Questions\n' + getListText(questions);

    copyToClipboard(text, event.target);
}

function getListText(ul) {
    const items = ul.querySelectorAll('li');
    return Array.from(items).map(li => {
        const task = li.querySelector('.action-task');
        const owner = li.querySelector('.action-owner');
        if (task) {
            return owner ? `- ${task.textContent} (${owner.textContent})` : `- ${task.textContent}`;
        }
        return `- ${li.textContent}`;
    }).join('\n');
}

function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('copied');
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    });
}

// email notification
async function sendEmail() {
    const emailInput = document.getElementById('email-input');
    const emailBtn = document.getElementById('email-btn');
    const email = emailInput.value.trim();

    if (!email) {
        showToast('Please enter an email address', 'error');
        return;
    }

    if (!currentFileId) {
        showToast('No meeting notes to send', 'error');
        return;
    }

    // basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showToast('Please enter a valid email address', 'error');
        return;
    }

    emailBtn.disabled = true;
    const originalText = emailBtn.innerHTML;
    emailBtn.innerHTML = '<span class="spinner"></span> Sending...';

    try {
        const response = await fetch(`/api/notify/${currentFileId}/email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || data.detail || 'Failed to send email');
        }

        showToast('Email sent successfully!', 'success');
        emailInput.value = '';

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        emailBtn.disabled = false;
        emailBtn.innerHTML = originalText;
    }
}

// slack notification
async function sendSlack() {
    const slackInput = document.getElementById('slack-input');
    const slackBtn = document.getElementById('slack-btn');
    const webhookUrl = slackInput.value.trim();

    if (!currentFileId) {
        showToast('No meeting notes to send', 'error');
        return;
    }

    slackBtn.disabled = true;
    const originalText = slackBtn.innerHTML;
    slackBtn.innerHTML = '<span class="spinner"></span> Sending...';

    try {
        const body = webhookUrl ? { webhook_url: webhookUrl } : {};

        const response = await fetch(`/api/notify/${currentFileId}/slack`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || data.detail || 'Failed to send to Slack');
        }

        showToast('Sent to Slack successfully!', 'success');
        slackInput.value = '';

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        slackBtn.disabled = false;
        slackBtn.innerHTML = originalText;
    }
}

// toast notification
function showToast(message, type = 'info') {
    // remove existing toast if any
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // auto-remove after 4 seconds
    setTimeout(() => {
        toast.remove();
    }, 4000);
}
