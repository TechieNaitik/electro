document.addEventListener('DOMContentLoaded', function() {
    const copyBtn = document.getElementById('copy-debug');
    
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            // We'll assume the HTML provides this data globally or via some mechanism
            if (!window.DEBUG_ERROR_CONFIG) {
                console.error('Debug configuration not found.');
                return;
            }

            const info = window.DEBUG_ERROR_CONFIG;

            const textToCopy = `
ERROR: ${info.type}
MESSAGE: ${info.message}
PATH: ${info.path}

LOCATION:
FILE: ${info.file}
LINE: ${info.line}
FUNC: ${info.func}

STACK TRACE:
${info.trace}
`.trim();

            navigator.clipboard.writeText(textToCopy).then(() => {
                const btn = this;
                const originalText = btn.innerText;
                btn.innerText = 'Copied!';
                btn.classList.add('copied');
                
                setTimeout(() => {
                    btn.innerText = originalText;
                    btn.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy info: ', err);
                // Fallback for older browsers or insecure contexts
                const textArea = document.createElement("textarea");
                textArea.value = textToCopy;
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    btn.innerText = 'Copied!';
                    btn.classList.add('copied');
                    setTimeout(() => {
                        btn.innerText = originalText;
                        btn.classList.remove('copied');
                    }, 2000);
                } catch (e) {
                    alert('Failed to copy to clipboard.');
                }
                document.body.removeChild(textArea);
            });
        });
    }
});
