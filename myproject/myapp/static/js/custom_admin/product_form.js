document.addEventListener('DOMContentLoaded', function() {
    // 1. Handle Deletion Toggles (Mark for deletion)
    const deleteCheckboxes = document.querySelectorAll('input[type="checkbox"][name$="-DELETE"]');
    deleteCheckboxes.forEach(checkbox => {
        // Initial state logic
        if (checkbox.checked) {
            checkbox.closest('.gallery-card').classList.add('marked-for-deletion');
        }

        checkbox.addEventListener('change', function() {
            const card = this.closest('.gallery-card');
            if (this.checked) {
                card.classList.add('marked-for-deletion');
            } else {
                card.classList.remove('marked-for-deletion');
            }
        });
    });

    // 2. Handle File Selection Success Message (No Preview version)
    const fileInputs = document.querySelectorAll('.gallery-upload-slot input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const inputId = this.id;
            const successMsg = document.getElementById('success-' + inputId);
            const placeholder = document.getElementById('placeholder-' + inputId);
            const label = document.getElementById('label-' + inputId);
            const cardInner = this.closest('.gallery-card-inner');

            if (this.files && this.files[0]) {
                // 1. Switch Visibility
                if (successMsg) successMsg.classList.remove('d-none');
                if (placeholder) placeholder.classList.add('d-none');
                
                // 2. Highlight Card
                if (cardInner) {
                    cardInner.style.borderColor = 'var(--success)';
                    cardInner.style.borderStyle = 'solid';
                    cardInner.style.background = 'rgba(0, 206, 201, 0.05)';
                }
                
                // 3. Set Filename
                if (label) label.textContent = "✓ " + this.files[0].name;
            } else {
                // Reset State
                if (successMsg) successMsg.classList.add('d-none');
                if (placeholder) placeholder.classList.remove('d-none');
                if (label) label.textContent = "";
                if (cardInner) {
                    cardInner.style.borderColor = 'var(--border-color)';
                    cardInner.style.borderStyle = 'dashed';
                    cardInner.style.background = 'var(--bg-secondary)';
                }
            }
        });
    });
});
