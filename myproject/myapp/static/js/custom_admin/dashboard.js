// Set active page for sidebar highlight
document.addEventListener("DOMContentLoaded", function () {
    const navDashboard = document.getElementById("nav-dashboard");
    if (navDashboard) navDashboard.classList.add("active");

    // Currency Refresh Logic
    const refreshCard = document.getElementById('currency-refresh-card');
    const refreshConfig = document.getElementById('currency-refresh-config');

    if (refreshCard && refreshConfig) {
        refreshCard.addEventListener('click', function () {
            const card = this;
            const icon = card.querySelector('.fa-rotate');
            const label = card.querySelector('.stat-number');
            const url = refreshConfig.dataset.url;
            const csrf = refreshConfig.dataset.csrf;

            // Start animation
            icon.classList.add('fa-spin');
            label.innerText = 'Syncing...';
            card.style.pointerEvents = 'none';
            card.style.opacity = '0.7';

            fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrf,
                    "Content-Type": "application/json"
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    label.innerText = 'Refreshed!';
                    label.style.color = 'var(--success)';
                    setTimeout(() => {
                        label.innerText = 'Click to Sync';
                        label.style.color = 'var(--text-secondary)';
                    }, 3000);
                } else {
                    label.innerText = 'Error!';
                    alert("Error refreshing rates: " + data.message);
                }
            })
            .catch(error => {
                console.error("Error:", error);
                label.innerText = 'Failed!';
            })
            .finally(() => {
                icon.classList.remove('fa-spin');
                card.style.pointerEvents = 'auto';
                card.style.opacity = '1';
            });
        });
    }
});
