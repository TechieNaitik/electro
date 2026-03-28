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

    const progress = document.getElementById('testProgress');
    const iframe = document.getElementById('reportIframe');
    const container = document.getElementById('reportContainer');
    const placeholder = document.getElementById('reportPlaceholder');
    const terminalContainer = document.getElementById('liveTerminalContainer');
    const terminalText = document.getElementById('liveTerminalText');
    const terminalStatus = document.getElementById('terminalStatus');

    // UI Setup
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Testing...';
    progress.style.display = 'flex';

    // Hide Report & Show Terminal
    if (container) container.classList.remove('visible');
    if (placeholder) placeholder.classList.remove('visible');
    terminalContainer.style.display = 'block';
    terminalText.textContent = '> Initializing Pytest Engine...\n';
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
            terminalText.textContent += chunk;

            // Auto scroll
            terminalText.parentElement.scrollTop = terminalText.parentElement.scrollHeight;
        }

        terminalStatus.textContent = 'FINISHED';
        terminalStatus.style.color = 'var(--success)';

        // Final UI cleanup
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play" style="margin-right:5px;"></i> Run Tests';
        progress.style.display = 'none';

        // Refresh Iframe & Show after a short delay
        setTimeout(() => {
            terminalContainer.style.display = 'none';
            if (container) {
                container.classList.add('visible');
                const timestamp = new Date().getTime();
                iframe.src = config.reportBaseUrl + '?t=' + timestamp;
            }
        }, 300);




    } catch (error) {
        console.error("Stream Error:", error);
        terminalText.textContent += "\n[ERROR] Connection lost or server error.\n";
        terminalStatus.textContent = 'ERROR';
        terminalStatus.style.color = 'var(--danger)';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play" style="margin-right:5px;"></i> Run Tests';
    }
}
