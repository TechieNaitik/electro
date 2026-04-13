document.addEventListener('DOMContentLoaded', function() {
    // Generalized dynamic row script 
    function setupFormset(containerId, rowClass, btnId, templateId, isSelect) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const rows = Array.from(container.querySelectorAll('.' + rowClass));
        const addBtn = document.getElementById(btnId);
        
        let hiddenPrefix = "attributes";
        let formTotal = document.querySelector(`input[name="${hiddenPrefix}-TOTAL_FORMS"]`);
        
        // Safe fallback in case relations are internally mapped differently
        if (!formTotal) {
            hiddenPrefix = 'variantattribute_set';
            formTotal = document.querySelector(`input[name="${hiddenPrefix}-TOTAL_FORMS"]`);
        }
        
        if(!formTotal) return;
        
        const template = document.getElementById(templateId).innerHTML;
        
        rows.forEach(row => {
            let isEmpty = false;
            const select = row.querySelector('select');
            if (select && select.value === '') isEmpty = true;
            
            const idInput = row.querySelector('input[name$="-id"]');
            if (isEmpty && (!idInput || !idInput.value)) {
                row.style.display = 'none';
            }
        });
        

        addBtn.addEventListener('click', function(e) {
            e.preventDefault();
            let hiddenRow = Array.from(container.querySelectorAll('.' + rowClass)).find(r => r.style.display === 'none');
            
            let targetDisplay = 'flex';
            
            if (hiddenRow) {
                hiddenRow.style.display = targetDisplay;
                hiddenRow.animate([{opacity: 0}, {opacity: 1}], {duration: 300, fill: 'forwards'});
            } else {
                let currentIndex = parseInt(formTotal.value);
                let newHtml = template.replace(/__prefix__/g, currentIndex);
                
                let tempDiv = document.createElement('div');
                tempDiv.innerHTML = newHtml;
                let newRow = tempDiv.firstElementChild;
                
                newRow.style.display = targetDisplay;
                container.appendChild(newRow);
                newRow.animate([{opacity: 0, transform: 'translateY(10px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: 300, fill: 'forwards'});
                
                formTotal.value = currentIndex + 1;
            }
        });
    }
    
    setupFormset('attr-container', 'attr-row', 'add-attr-btn', 'attr-empty-template', true);
    
    document.addEventListener('click', function(e) {
        let removeLabel = e.target.closest('label');
        if (removeLabel && removeLabel.textContent.includes('REMOVE')) {
            let row = removeLabel.closest('.attr-row');
            if (row) {
                row.style.transition = "all 0.3s ease";
                row.style.opacity = '0.3';
                row.style.pointerEvents = 'none';
                row.style.transform = 'scale(0.98)';
            }
        }
    });

    // Administrative submit protection
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function() {
            const btn = document.getElementById('admin-variant-submit');
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'Syncing...';
                btn.classList.add('opacity-50');
            }
        });
    }
});

