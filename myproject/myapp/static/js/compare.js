/**
 * Product Comparison Feature Logic
 * Manages localStorage for comparison tray and interactivity.
 * Features: Compare Tray, Highlight Differences, Qty Selector, Wishlist Integration
 */

document.addEventListener('DOMContentLoaded', function () {
    const COMPARE_STORAGE_KEY = 'electro_compare_list';
    const MAX_COMPARE_ITEMS = 4;

    // Initialize tray state
    updateCompareTray();

    // =========================================================================
    //  EVENT DELEGATION — Central click handler
    // =========================================================================
    document.body.addEventListener('click', function (e) {
        // ── Compare Toggle (product cards) ──
        const toggleBtn = e.target.closest('.compare-toggle-btn');
        if (toggleBtn) {
            e.preventDefault();
            const productId   = toggleBtn.getAttribute('data-product-id');
            const productName = toggleBtn.getAttribute('data-product-name');
            const productImage = toggleBtn.getAttribute('data-product-image');
            toggleCompare(productId, productName, productImage);
        }

        // ── Remove from tray / compare table ──
        const removeBtn = e.target.closest('.remove-from-tray, .compare-remove-btn');
        if (removeBtn) {
            e.preventDefault();
            const productId = removeBtn.getAttribute('data-product-id');
            removeFromCompare(productId);
        }

        // ── Quantity: Minus ──
        const minusBtn = e.target.closest('.compare-qty-minus');
        if (minusBtn) {
            const input = minusBtn.closest('.compare-qty-group').querySelector('.compare-qty-input');
            const min   = parseInt(input.min) || 1;
            const cur   = parseInt(input.value) || 1;
            if (cur > min) {
                input.value = cur - 1;
                syncCartLink(input);
            }
        }

        // ── Quantity: Plus ──
        const plusBtn = e.target.closest('.compare-qty-plus');
        if (plusBtn) {
            const input = plusBtn.closest('.compare-qty-group').querySelector('.compare-qty-input');
            const max   = parseInt(input.max) || 99;
            const cur   = parseInt(input.value) || 1;
            if (cur < max) {
                input.value = cur + 1;
                syncCartLink(input);
            }
        }
    });

    // Also handle manual typing in qty inputs
    document.querySelectorAll('.compare-qty-input').forEach(function (input) {
        input.addEventListener('change', function () {
            const min = parseInt(this.min) || 1;
            const max = parseInt(this.max) || 99;
            let val = parseInt(this.value) || 1;
            val = Math.max(min, Math.min(max, val));
            this.value = val;
            syncCartLink(this);
        });
    });

    /**
     * Syncs the Add-to-Cart link href with the current qty value.
     */
    function syncCartLink(input) {
        const pid  = input.getAttribute('data-product-id');
        const qty  = input.value;
        const cell = input.closest('td');
        if (!cell) return;
        const cartLink = cell.querySelector('.compare-cart-btn');
        if (cartLink) {
            const baseHref = cartLink.href.split('?')[0];
            cartLink.href = `${baseHref}?qty=${qty}`;
        }
    }

    // =========================================================================
    //  COMPARE CORE FUNCTIONS
    // =========================================================================
    function toggleCompare(id, name, image) {
        let compareList = getCompareList();
        const index = compareList.findIndex(item => item.id == id);

        if (index > -1) {
            compareList.splice(index, 1);
            notify('Product removed from comparison.');
        } else {
            if (compareList.length >= MAX_COMPARE_ITEMS) {
                alert(`You can only compare up to ${MAX_COMPARE_ITEMS} products at a time.`);
                return;
            }
            compareList.push({ id, name, image });
            notify(`${name} added to comparison.`);
        }

        saveCompareList(compareList);
        updateCompareTray();
        updateButtonStates();
    }

    function removeFromCompare(id) {
        let compareList = getCompareList();
        const newList = compareList.filter(item => item.id != id);
        saveCompareList(newList);
        updateCompareTray();
        updateButtonStates();

        if (window.location.pathname.includes('/compare/')) {
            const ids = newList.map(item => item.id).join(',');
            if (ids) {
                window.location.href = `/compare/?ids=${ids}`;
            } else {
                window.location.href = '/shop/';
            }
        }
    }

    // =========================================================================
    //  STORAGE HELPERS
    // =========================================================================
    function getCompareList() {
        const stored = localStorage.getItem(COMPARE_STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    }

    function saveCompareList(list) {
        localStorage.setItem(COMPARE_STORAGE_KEY, JSON.stringify(list));
    }

    // =========================================================================
    //  UI UPDATES — Tray & Button States
    // =========================================================================
    function updateCompareTray() {
        const tray = document.getElementById('compare-tray');
        const itemsContainer = document.getElementById('compare-tray-items');
        if (!tray || !itemsContainer) return;

        const compareList = getCompareList();

        if (compareList.length > 0) {
            tray.classList.add('show');
            itemsContainer.innerHTML = compareList.map(item => `
                <div class="compare-item-thumb">
                    <img src="${item.image}" alt="${item.name}">
                    <button class="remove-from-tray" data-product-id="${item.id}" title="Remove">&times;</button>
                </div>
            `).join('');

            const compareBtn = tray.querySelector('.compare-now-btn');
            if (compareBtn) {
                const ids = compareList.map(item => item.id).join(',');
                compareBtn.href = `/compare/?ids=${ids}`;
            }

            const countLabel = tray.querySelector('.compare-count');
            if (countLabel) countLabel.innerText = `${compareList.length}/${MAX_COMPARE_ITEMS}`;
        } else {
            tray.classList.remove('show');
        }
    }

    function updateButtonStates() {
        const compareList = getCompareList().map(item => item.id);
        document.querySelectorAll('.compare-toggle-btn').forEach(btn => {
            const id = btn.getAttribute('data-product-id');
            if (compareList.includes(id)) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    updateButtonStates();

    // =========================================================================
    //  DESCRIPTION EXPANSION
    // =========================================================================
    document.querySelectorAll('.toggle-desc').forEach(btn => {
        btn.addEventListener('click', function () {
            const cell     = this.closest('td').querySelector('.description-cell');
            const fullDesc = cell.querySelector('.full-description');

            if (fullDesc.style.display === 'none' || fullDesc.style.display === '') {
                fullDesc.style.display = 'block';
                this.textContent = 'Show Less';
            } else {
                fullDesc.style.display = 'none';
                this.textContent = 'Show More';
            }
        });
    });

    // =========================================================================
    //  HIGHLIGHT LOWEST PRICE
    // =========================================================================
    function highlightLowestPrice() {
        const priceCells = document.querySelectorAll('.product-price-value');
        if (priceCells.length < 2) return;

        let minPrice = Infinity;
        let lowestCells = [];

        priceCells.forEach(cell => {
            const price = parseFloat(cell.getAttribute('data-price'));
            if (price < minPrice) {
                minPrice = price;
                lowestCells = [cell];
            } else if (price === minPrice) {
                lowestCells.push(cell);
            }
        });

        lowestCells.forEach(cell => {
            cell.parentElement.classList.add('lowest-price-cell');
        });
    }

    if (window.location.pathname.includes('/compare/')) {
        highlightLowestPrice();
    }

    // =========================================================================
    //  HIGHLIGHT DIFFERENCES TOGGLE
    // =========================================================================
    const highlightToggle = document.getElementById('highlightDiffToggle');
    if (highlightToggle) {
        highlightToggle.addEventListener('change', function () {
            applyHighlightDiff(this.checked);
        });
    }

    /**
     * Scans every data row marked with [data-compare-row].
     * If all data-value cells have identical content → same (muted bg).
     * If at least one differs → different (yellow highlight).
     * When toggled off, clears all classes.
     */
    function applyHighlightDiff(active) {
        const rows = document.querySelectorAll('#compareTable tbody tr[data-compare-row]');

        rows.forEach(function (row) {
            const dataCells = row.querySelectorAll('td[data-value]');
            if (!dataCells.length) return;

            // Clear previous highlights
            dataCells.forEach(td => {
                td.classList.remove('diff-highlight', 'diff-same');
            });

            if (!active) return;

            // Collect normalized values
            const values = Array.from(dataCells).map(td =>
                (td.getAttribute('data-value') || '').trim().toLowerCase()
            );

            const allSame = values.every(v => v === values[0]);

            dataCells.forEach(td => {
                td.classList.add(allSame ? 'diff-same' : 'diff-highlight');
            });
        });
    }

    // =========================================================================
    //  WISHLIST INTEGRATION on Compare Page
    // =========================================================================
    document.querySelectorAll('.compare-wishlist-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const pid   = this.getAttribute('data-product-id');
            const label = this.querySelector('.wishlist-label');
            const icon  = this.querySelector('i');
            const self  = this;

            fetch(`/toggle-wishlist/${pid}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    if (data.action === 'added') {
                        self.classList.add('wishlisted');
                        icon.classList.remove('far');
                        icon.classList.add('fas');
                        if (label) label.textContent = 'In Wishlist';
                    } else {
                        self.classList.remove('wishlisted');
                        icon.classList.remove('fas');
                        icon.classList.add('far');
                        if (label) label.textContent = 'Add to Wishlist';
                    }
                    notify(data.message, 'success');
                } else {
                    notify(data.message || 'Please log in to use the wishlist.', 'error');
                }
            })
            .catch(() => {
                notify('Something went wrong. Please try again.', 'error');
            });
        });
    });

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.trim().split('=')[1] : '';
    }
});

// =========================================================================
//  UTILITY: Generic Notification (uses global showNotification if available)
// =========================================================================
function notify(msg, type = 'success') {
    if (typeof showNotification === 'function') {
        showNotification(msg, type);
    } else {
        console.log(`[${type}] ${msg}`);
    }
}
