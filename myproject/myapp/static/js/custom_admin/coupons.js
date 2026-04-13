document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.progress-bar-fill').forEach(el => {
        const progress = el.dataset.progress || 0;
        el.style.width = progress + '%';
    });
});
