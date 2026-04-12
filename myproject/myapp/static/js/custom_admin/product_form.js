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

    // 2. Handle File Selection and Live Preview
    const fileInputs = document.querySelectorAll('.gallery-upload-slot input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const inputId = this.id;
            const successMsg = document.getElementById('success-' + inputId);
            const placeholder = document.getElementById('placeholder-' + inputId);
            const label = document.getElementById('label-' + inputId);
            const preview = document.getElementById('preview-' + inputId);
            const cardInner = this.closest('.gallery-card-inner');

            if (this.files && this.files[0]) {
                const file = this.files[0];
                
                // 1. Generate Live Preview
                if (preview) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        preview.src = e.target.result;
                        preview.classList.remove('d-none');
                    }
                    reader.readAsDataURL(file);
                }

                // 2. Switch Visibility
                if (successMsg) successMsg.classList.remove('d-none');
                if (placeholder) placeholder.classList.add('d-none');
                
                // 3. Highlight Card
                if (cardInner) {
                    cardInner.style.borderColor = 'var(--success)';
                    cardInner.style.borderStyle = 'solid';
                    cardInner.style.background = 'rgba(0, 206, 201, 0.05)';
                }
                
                // 4. Set Filename
                if (label) {
                    label.textContent = "✓ " + file.name;
                    label.classList.add('text-success');
                }
            } else {
                // Reset State
                if (preview) {
                    preview.src = "";
                    preview.classList.add('d-none');
                }
                if (successMsg) successMsg.classList.add('d-none');
                if (placeholder) placeholder.classList.remove('d-none');
                if (label) {
                    label.textContent = "";
                    label.classList.remove('text-success');
                }
                if (cardInner) {
                    cardInner.style.borderColor = 'var(--border-color)';
                    cardInner.style.borderStyle = 'dashed';
                    cardInner.style.background = 'var(--bg-secondary)';
                }
            }
        });
    });
});
