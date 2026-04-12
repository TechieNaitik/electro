/**
 * Common JavaScript for Electro Site Admin Panel
 */

/**
 * Open the export modal for a specific module
 * @param {string} module - The name of the module (e.g., 'Products', 'Orders', 'Customers')
 */
function openExportModal(module) {
    const exportModuleInput = document.getElementById('exportModule');
    if (exportModuleInput) exportModuleInput.value = module;
    
    // Get current 'q' from URL and add to form if it exists
    const urlParams = new URLSearchParams(window.location.search);
    const q = urlParams.get('q');
    
    // Remove existing hidden q if any
    const existingQ = document.getElementById('exportQ');
    if (existingQ) existingQ.remove();
    
    if (q) {
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = 'q';
        hiddenInput.id = 'exportQ';
        hiddenInput.value = q;
        const exportForm = document.getElementById('exportForm');
        if (exportForm) exportForm.appendChild(hiddenInput);
    }

    const modal = document.getElementById('exportModal');
    const loading = document.getElementById('exportLoading');
    const submitBtn = document.getElementById('exportSubmitBtn');

    if (modal) modal.classList.add('open');
    if (loading) loading.style.display = 'none';
    if (submitBtn) submitBtn.disabled = false;
}

/**
 * Close the export modal
 */
function closeExportModal() {
    const modal = document.getElementById('exportModal');
    if (modal) modal.classList.remove('open');
}

// Initialize export form listener
document.addEventListener('DOMContentLoaded', () => {
    const exportForm = document.getElementById('exportForm');
    if (exportForm) {
        exportForm.addEventListener('submit', function(e) {
            const loading = document.getElementById('exportLoading');
            const submitBtn = document.getElementById('exportSubmitBtn');
            
            if (loading) loading.style.display = 'block';
            if (submitBtn) submitBtn.disabled = true;
            
            // Close the modal after a short delay since we can't detect download completion
            setTimeout(() => {
                closeExportModal();
            }, 3000);
        });
    }

    // Close modal when clicking outside
    window.onclick = function(event) {
        const modal = document.getElementById('exportModal');
        if (event.target == modal) {
            closeExportModal();
        }
    }

    // ───────── Instant Search ─────────
    let searchTimeout = null;
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('instant-search')) {
            clearTimeout(searchTimeout);
            const query = e.target.value;
            const form = e.target.closest('form');
            const containerId = 'data-container';
            
            searchTimeout = setTimeout(() => {
                const url = new URL(window.location.href);
                url.searchParams.set('q', query);
                url.searchParams.delete('page'); // Reset to page 1 on search
                
                const container = document.getElementById(containerId);
                if (container) container.style.opacity = '0.5';

                fetch(url)
                    .then(response => response.text())
                    .then(html => {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        const newContent = doc.getElementById(containerId);
                        if (newContent && container) {
                            container.innerHTML = newContent.innerHTML;
                            container.style.opacity = '1';
                            
                            // Update URL without reloading
                            window.history.pushState({}, '', url);
                        }
                    })
                    .catch(err => console.error('Search failed:', err));
            }, 300);
        }
    });

    // ───────── Alert Auto-dismiss ─────────
    setTimeout(() => {
        document.querySelectorAll('.alert-message').forEach(alert => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => {
                if (alert.parentNode) alert.remove();
            }, 500);
        });
    }, 5000);

    // ───────── Number Input Scroll Fix ─────────
    // Prevents "on its own" stock changes when scrolling the form with mouse over number inputs
    document.addEventListener('wheel', function(e) {
        if (document.activeElement.type === 'number') {
            document.activeElement.blur();
        }
    });

    // Also disable arrow key changes if needed for critical fields
    document.addEventListener('keydown', function(e) {
        if (['ArrowUp', 'ArrowDown'].includes(e.key) && document.activeElement.type === 'number') {
            // Optional: e.preventDefault(); 
            // Better to let them use arrows if they explicitly clicked/tabbed in
        }
    });
});
