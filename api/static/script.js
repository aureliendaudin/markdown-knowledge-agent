const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const statusIndicator = document.getElementById('status');

let isConnected = false;

// Auto-resize textarea
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    if (this.value === '') {
        this.style.height = 'auto';
    }
});

// Handle Enter key
userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

// Check health
async function checkHealth() {
    try {
        const response = await fetch('/health');
        if (response.ok) {
            const data = await response.json();
            isConnected = true;
            statusIndicator.textContent = 'Connected';
            statusIndicator.className = 'status-indicator connected';
            console.log('Active modules:', data.modules_active);
        } else {
            throw new Error('Health check failed');
        }
    } catch (error) {
        isConnected = false;
        statusIndicator.textContent = 'Disconnected';
        statusIndicator.className = 'status-indicator error';
        console.error('Connection error:', error);
    }
}

// Initial check
checkHealth();
setInterval(checkHealth, 30000);

const logsContent = document.getElementById('logs-content');

// ... (existing code)

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Add user message
    addMessage(text, 'user');
    userInput.value = '';
    userInput.style.height = 'auto';
    
    // Clear previous logs for new request
    clearLogs();
    addLog('Request sent...', 'info');
    
    // Disable input
    userInput.disabled = true;
    sendBtn.disabled = true;
    
    // Add loading indicator
    const loadingId = addLoadingMessage();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: text })
        });

        // Remove loading indicator
        removeMessage(loadingId);

        if (response.ok) {
            const data = await response.json();
            addMessage(data.response, 'bot');
            
            // Display logs
            if (data.logs && data.logs.length > 0) {
                data.logs.forEach(log => addLog(log, 'info'));
            }
            addLog(`Processing time: ${data.processing_time.toFixed(2)}s`, 'info');
            
        } else {
            const errorData = await response.json();
            addMessage(`Error: ${errorData.detail || 'Something went wrong'}`, 'system');
            addLog(`Error: ${errorData.detail}`, 'error');
        }
    } catch (error) {
        removeMessage(loadingId);
        addMessage(`Network Error: ${error.message}`, 'system');
        addLog(`Network Error: ${error.message}`, 'error');
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
    }
}

function addLog(text, type) {
    const logDiv = document.createElement('div');
    logDiv.className = `log-entry ${type}`;
    logDiv.textContent = text;
    logsContent.appendChild(logDiv);
    logsContent.scrollTop = logsContent.scrollHeight;
}

function clearLogs() {
    logsContent.innerHTML = '';
}

function addMessage(text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    
    if (type === 'bot') {
        contentDiv.innerHTML = marked.parse(text);
    } else {
        contentDiv.textContent = text;
    }
    
    msgDiv.appendChild(contentDiv);
    chatHistory.appendChild(msgDiv);
    
    // Scroll to bottom
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    return msgDiv;
}

function addLoadingMessage() {
    const id = 'loading-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.id = id;
    msgDiv.className = 'message bot';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    contentDiv.innerHTML = '<em>Thinking...</em>';
    
    msgDiv.appendChild(contentDiv);
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    return id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
