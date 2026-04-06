document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('values-container');
    const addBtn = document.getElementById('add-row-btn');
    const totalFormsInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
    const template = document.getElementById('empty-form-template').innerHTML;
    
    // Initially hide any entirely blank forms so the user can 'add' them dynamically
    let visibleCount = 0;
    Array.from(container.querySelectorAll('.val-row')).forEach(row => {
        const valueInput = row.querySelector('input[name$="-value"]');
        const idInput = row.querySelector('input[name$="-id"]');
        if (valueInput && !valueInput.value && (!idInput || !idInput.value)) {
            row.style.display = 'none';
        } else {
            visibleCount++;
        }
    });
    
    // Do not show any empty rows by default inline with pure fluid requirements.
    // Empty rows are only appended when the user explicitly clicks the Add button.
    
    addBtn.addEventListener('click', function(e) {
        e.preventDefault();
        // Find first hidden empty row
        let hiddenRow = Array.from(container.querySelectorAll('.val-row')).find(row => row.style.display === 'none');
        
        if (hiddenRow) {
            hiddenRow.style.display = 'flex';
            hiddenRow.animate([{opacity: 0}, {opacity: 1}], {duration: 300, fill: 'forwards'});
        } else {
            // If no hidden rows exist, we dynamically clone and inject a new one using Django's empty form
            let currentIndex = parseInt(totalFormsInput.value);
            let newHtml = template.replace(/__prefix__/g, currentIndex);
            
            let tempDiv = document.createElement('div');
            tempDiv.innerHTML = newHtml;
            let newRow = tempDiv.firstElementChild;
            
            newRow.style.display = 'flex';
            container.appendChild(newRow);
            newRow.animate([{opacity: 0, transform: 'translateY(10px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: 300, fill: 'forwards'});
            
            totalFormsInput.value = currentIndex + 1;
        }
    });
    
    // Handle logical UI deletion (fade out row visually while leaving checkbox ticked for Django backend processing)
    container.addEventListener('click', function(e) {
        let removeLabel = e.target.closest('label');
        if (removeLabel && removeLabel.textContent.includes('REMOVE')) {
            let row = removeLabel.closest('.val-row');
            if (row) {
                row.style.transition = "all 0.3s ease";
                row.style.opacity = '0.3';
                row.style.pointerEvents = 'none';
                row.style.transform = 'scale(0.98)';
            }
        }
    });
});
