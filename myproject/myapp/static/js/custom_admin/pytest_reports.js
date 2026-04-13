async function runPytest() {
    const btn = document.getElementById('runTestsBtn');
    
    // Config Extraction
    let config = window.PYTEST_CONFIG;
    if (!config && btn) {
        config = {
            streamUrl: btn.dataset.streamUrl,
            reportBaseUrl: btn.dataset.reportBaseUrl,
            csrfToken: btn.dataset.csrfToken
        };
    }

    if (!config) {
        console.error("Pytest configuration not found.");
        return;
    }

    const iframe = document.getElementById('reportIframe');
    const container = document.getElementById('reportContainer');
    const placeholder = document.getElementById('reportPlaceholder');
    const terminalContainer = document.getElementById('liveTerminalContainer');
    const terminalText = document.getElementById('liveTerminalText');
    const terminalStatus = document.getElementById('terminalStatus');

    // UI Setup
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Testing...';

    // Hide Report & Show Terminal
    if (container) container.classList.remove('visible');
    if (placeholder) placeholder.classList.remove('visible');
    terminalContainer.style.display = 'block';
    terminalText.innerHTML = '<span style="color:var(--accent-light)">> Initializing Pytest Engine...</span><br>';
    terminalStatus.textContent = 'RUNNING';
    terminalStatus.style.color = 'var(--accent-light)';

    try {
        const response = await fetch(config.streamUrl);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            // Convert ANSI to HTML for colors
            terminalText.innerHTML += ansiToHtml(chunk);

            // Auto scroll
            terminalText.parentElement.scrollTop = terminalText.parentElement.scrollHeight;
        }

        terminalStatus.textContent = 'FINISHED';
        terminalStatus.style.color = 'var(--success)';

        // Final UI cleanup
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play" style="margin-right:5px;"></i> Run Tests';
        
        console.log("Test execution finished. Terminal remains visible.");
        
        // Enable report buttons
        document.querySelectorAll('.report-btn').forEach(l => l.classList.remove('disabled'));

    } catch (error) {
        console.error("Stream Error:", error);
        terminalText.innerHTML += "\n<span style='color:var(--danger)'>[ERROR] Connection lost or server error.</span>\n";
        terminalStatus.textContent = 'ERROR';
        terminalStatus.style.color = 'var(--danger)';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play" style="margin-right:5px;"></i> Run Tests';
    }
}

// Simple ANSI to HTML converter for Terminal Colors
function ansiToHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\u001b\[31m/g, '<span style="color:#ff5555">') // Red
        .replace(/\u001b\[32m/g, '<span style="color:#50fa7b">') // Green
        .replace(/\u001b\[33m/g, '<span style="color:#f1fa8c">') // Yellow
        .replace(/\u001b\[34m/g, '<span style="color:#8be9fd">') // Cyan (Blue-ish)
        .replace(/\u001b\[35m/g, '<span style="color:#ff79c6">') // Magenta
        .replace(/\u001b\[36m/g, '<span style="color:#8be9fd">') // Cyan
        .replace(/\u001b\[0;31;40m/g, '<span style="color:#ff5555">') // Red variant
        .replace(/\u001b\[0;32;40m/g, '<span style="color:#50fa7b">') // Green variant
        .replace(/\u001b\[1m/g, '<b>')                          // Bold
        .replace(/\u001b\[0m/g, '</span></b>')                  // reset
        .replace(/\r\n/g, '<br>')
        .replace(/\n/g, '<br>');
}
