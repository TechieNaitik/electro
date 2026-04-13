document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.color-dot').forEach(dot => {
        const color = dot.getAttribute('data-bg-color');
        if (color) {
            dot.style.backgroundColor = color;
        }
    });
});
