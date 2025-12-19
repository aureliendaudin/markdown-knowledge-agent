const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const statusIndicator = document.getElementById('status');

let isConnected = false;

// Auto-resize textarea
userInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    if (this.value === '') {
        this.style.height = 'auto';
    }
});

// Handle Enter key
userInput.addEventListener('keydown', function (e) {
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
const modulesList = document.getElementById('modules-list');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const sidebar = document.querySelector('.sidebar');
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

let activeModules = {}; // Store module states

// Tabs Logic
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => {
            c.classList.remove('active');
            c.style.display = 'none';
        });

        // Add active class to clicked
        btn.classList.add('active');
        const tabId = btn.dataset.tab;
        const content = document.getElementById(`${tabId}-view`);
        content.classList.add('active');
        content.style.display = 'flex';

        // If graph tab, render graph
        if (tabId === 'graph') {
            renderGraph();
        }
    });
});

document.getElementById('refresh-graph').addEventListener('click', renderGraph);

let network = null;

async function renderGraph() {
    try {
        const response = await fetch('/memory');
        if (!response.ok) return;
        const data = await response.json();

        const nodes = [];
        const edges = [];
        const concepts = data.concepts || {};
        const conceptIndex = data.concept_index || {};

        // Create Nodes
        Object.keys(concepts).forEach(concept => {
            const info = concepts[concept];
            nodes.push({
                id: concept,
                label: concept,
                value: info.count, // Size based on frequency
                title: `Count: ${info.count}\nFirst Seen: ${info.first_seen}`,
                color: {
                    background: '#e0f2fe',
                    border: '#0284c7'
                }
            });
        });

        // Create Edges (Co-occurrence)
        // 1. Invert index: message_idx -> [concepts]
        const msgToConcepts = {};
        Object.keys(conceptIndex).forEach(concept => {
            conceptIndex[concept].forEach(idx => {
                if (!msgToConcepts[idx]) msgToConcepts[idx] = [];
                msgToConcepts[idx].push(concept);
            });
        });

        // 2. Create edges for concepts in same message
        const edgeMap = {}; // "conceptA-conceptB" -> weight

        Object.values(msgToConcepts).forEach(conceptList => {
            if (conceptList.length < 2) return;

            for (let i = 0; i < conceptList.length; i++) {
                for (let j = i + 1; j < conceptList.length; j++) {
                    const c1 = conceptList[i];
                    const c2 = conceptList[j];
                    const id = [c1, c2].sort().join('-');

                    if (!edgeMap[id]) edgeMap[id] = 0;
                    edgeMap[id]++;
                }
            }
        });

        Object.keys(edgeMap).forEach(id => {
            const [from, to] = id.split('-');
            edges.push({
                from,
                to,
                value: edgeMap[id], // Thickness based on co-occurrence
                color: { color: '#cbd5e1' }
            });
        });

        // Render
        const container = document.getElementById('mynetwork');
        const graphData = {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        };
        const options = {
            nodes: {
                shape: 'dot',
                font: {
                    size: 14,
                    face: 'Inter'
                }
            },
            physics: {
                stabilization: false,
                barnesHut: {
                    gravitationalConstant: -2000,
                    springConstant: 0.04,
                    springLength: 95
                }
            }
        };

        if (network) {
            network.setData(graphData);
        } else {
            network = new vis.Network(container, graphData, options);
        }

    } catch (error) {
        console.error("Error rendering graph:", error);
    }
}

// Toggle Sidebar
toggleSidebarBtn.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    toggleSidebarBtn.classList.toggle('active');
});

// Check health
async function checkHealth() {
    try {
        const response = await fetch('/health');
        if (response.ok) {
            const data = await response.json();
            isConnected = true;
            statusIndicator.textContent = 'Connected';
            statusIndicator.className = 'status-indicator connected';

            // Initialize modules list if empty
            if (modulesList.children.length === 0) {
                renderModules(data.modules_active);
            }
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

function renderModules(modules) {
    modulesList.innerHTML = '';

    // Default known modules if list is empty (fallback)
    const allModules = modules.length > 0 ? modules : ['retrieval', 'memory'];

    allModules.forEach(moduleName => {
        // Set default state to true
        activeModules[moduleName] = true;

        const item = document.createElement('div');
        item.className = 'module-item';

        const label = document.createElement('label');
        label.htmlFor = `mod-${moduleName}`;
        label.textContent = moduleName.charAt(0).toUpperCase() + moduleName.slice(1);

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `mod-${moduleName}`;
        checkbox.checked = true;

        checkbox.addEventListener('change', (e) => {
            activeModules[moduleName] = e.target.checked;
            addLog(`Module '${moduleName}' ${e.target.checked ? 'enabled' : 'disabled'}`, 'info');
        });

        item.appendChild(label);
        item.appendChild(checkbox);
        modulesList.appendChild(item);
    });
}

// Initial check
checkHealth();
setInterval(checkHealth, 30000);

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

    // Log active configuration
    const enabledMods = Object.keys(activeModules).filter(k => activeModules[k]);
    addLog(`Active modules: ${enabledMods.join(', ')}`, 'info');
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
            body: JSON.stringify({
                message: text,
                modules: activeModules
            })
        });

        // Remove loading indicator
        removeMessage(loadingId);

        if (response.ok) {
            const data = await response.json();
            addMessage(data.response, 'bot', data.context_used);

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

function addMessage(text, type, context = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';

    if (type === 'bot') {
        contentDiv.innerHTML = marked.parse(text);
        if (context && context.length > 0) {
            const contextDiv = document.createElement('div');
            contextDiv.className = 'memory-context';

            const header = document.createElement('div');
            header.className = 'context-header';
            header.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg> Used Memory (${context.length})`;
            header.onclick = () => {
                const details = contextDiv.querySelector('.context-details');
                details.style.display = details.style.display === 'none' ? 'block' : 'none';
            };

            const details = document.createElement('div');
            details.className = 'context-details';
            details.style.display = 'none';

            const pre = document.createElement('pre');
            pre.textContent = JSON.stringify(context, null, 2);
            details.appendChild(pre);

            contextDiv.appendChild(header);
            contextDiv.appendChild(details);
            contentDiv.appendChild(contextDiv);
        }
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

