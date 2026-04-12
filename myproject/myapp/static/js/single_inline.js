(function () {
    'use strict';

    const PRODUCT_ID    = window.PRODUCT_ID;
    const ALL_VARIANTS  = window.ALL_VARIANTS;

    // State: attr_name → selected attribute_value id (int) or null
    const selectedAttrs = {};

    const mainImg        = document.getElementById('main-product-image');
    const thumbStrip     = document.getElementById('thumbnail-strip');
    const variantPriceEl = document.getElementById('variant-price');
    const stockBadgeEl   = document.getElementById('stock-status-badge');
    const variantInput   = document.getElementById('selected-variant-id');
    const addToCartBtn   = document.getElementById('add-to-cart-btn');
    const variantSkuContainer = document.getElementById('variant-sku-container');
    const variantSkuValue     = document.getElementById('variant-sku-value');

    // ── Gallery swap with crossfade ───────────────────────────────────────────
    // ── Gallery Highlighting logic ───────────────────────────────────────────
    function highlightGallery(avIds) {
        if (!thumbStrip) return;
        const thumbnails = thumbStrip.querySelectorAll('.thumbnail-item');
        if (!thumbnails.length) return;

        // If no attributes selected, reset all to semi-neutral
        if (!avIds || !avIds.length) {
            thumbnails.forEach(t => {
                t.classList.remove('dimmed', 'highlighted');
            });
            return;
        }

        let firstMatch = null;

        thumbnails.forEach(t => {
            const tAvId = t.dataset.avId;
            // Highlight if it's a general image (no av_id) OR if it matches any selected avId
            const isGeneral = !tAvId;
            const isMatch   = avIds.includes(parseInt(tAvId));

            if (isMatch) {
                t.classList.add('highlighted');
                t.classList.remove('dimmed');
                if (!firstMatch) firstMatch = t;
            } else if (isGeneral) {
                t.classList.remove('dimmed', 'highlighted');
            } else {
                t.classList.add('dimmed');
                t.classList.remove('highlighted');
            }
        });

        // Smooth scroll to the first match if it exists
        if (firstMatch) {
            firstMatch.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            // Also trigger main image update to the first highlighted image
            const imgUrl = firstMatch.dataset.thumbUrl;
            if (imgUrl && mainImg.src !== imgUrl) {
                mainImg.classList.add('img-crossfade-out');
                setTimeout(() => {
                    mainImg.src = imgUrl;
                    mainImg.classList.remove('img-crossfade-out');
                }, 300);
                
                thumbnails.forEach(th => th.classList.remove('active'));
                firstMatch.classList.add('active');
            }
        }
    }

    // Initialize the existing thumbnails with click handlers (since we no longer clear the strip)
    if (thumbStrip) {
        thumbStrip.querySelectorAll('.thumbnail-item').forEach(div => {
            div.addEventListener('click', () => {
                const imgUrl = div.dataset.thumbUrl;
                thumbStrip.querySelectorAll('.thumbnail-item').forEach(t => t.classList.remove('active'));
                div.classList.add('active');
                
                mainImg.classList.add('img-crossfade-out');
                setTimeout(() => { 
                    mainImg.src = imgUrl; 
                    mainImg.classList.remove('img-crossfade-out'); 
                }, 300);

                // CONNECTION: If this thumbnail belongs to a variant color, select it
                const tAvId = parseInt(div.dataset.avId);
                if (tAvId) {
                    const el = document.querySelector(`[data-av-id="${tAvId}"]`);
                    if (el && el.dataset.attrName === 'Color' && !el.classList.contains('active')) {
                        el.click();
                    }
                }
            });
        });
    }

    function resolveVariant(avIds) {
        if (!avIds || avIds.length === 0) return null;
        
        // Use the O(1) matrix lookup. IDs are sorted to match the backend key format.
        const key = [...avIds].sort((a,b) => a - b).join(',');
        return ALL_VARIANTS[key] || null;
    }

    // ── Main UI update ────────────────────────────────────────────────────────
    function updateUI() {
        const avIds = Object.values(selectedAttrs).filter(Boolean);
        const resolvedVariant = resolveVariant(avIds);

        // Grey out unavailable combinations (Still O(N*A) but manageable for UI state)
        // We iterate over all possible attribute values to see if they are "viable" given other selections
        document.querySelectorAll('[data-av-id]').forEach(el => {
            const avId = parseInt(el.dataset.avId);
            const attrName = el.dataset.attrName;
            
            // Collect other selected IDs
            const otherIds = Object.entries(selectedAttrs)
                .filter(([k]) => k !== attrName)
                .map(([, v]) => v).filter(Boolean);
            
            // Check if ANY variant exists in the matrix that contains both otherIds and this avId
            const isViable = Object.values(ALL_VARIANTS).some(v => 
                [...otherIds, avId].every(id => {
                    // This is slightly tricky since the matrix values don't store attribute_ids directly
                    // but we can infer them from the keys or use simple stock check if preferred.
                    // For now, let's keep it simple: if this avId + otherIds results in a key that exists
                    // we need to be careful with "partial" keys.
                    
                    // Actually, simpler logic: a value is viable if there exists AT LEAST ONE 
                    // variant in ALL_VARIANTS that has this avId AND all otherIds.
                    return true; // Placeholder for now or keep existing logic if we adjust models
                })
            );
            
            // Re-implementing viable check correctly for the new matrix
            const viable = Object.keys(ALL_VARIANTS).some(key => {
                const parts = key.split(',').map(Number);
                return [...otherIds, avId].every(id => parts.includes(id));
            });

            el.classList.toggle('unavailable', !viable);
        });

        // Price & SKU
        if (resolvedVariant) {
            variantPriceEl.textContent = '₹' + parseFloat(resolvedVariant.price).toLocaleString('en-IN');
            variantInput.value = resolvedVariant.id;
            
            // Update SKU
            if (variantSkuValue && variantSkuContainer) {
                variantSkuValue.textContent = resolvedVariant.sku || 'N/A';
                variantSkuContainer.style.display = 'block';
            }
        } else {
            variantInput.value = '';
            // Reset price to product base
            const basePrice = variantPriceEl.getAttribute('data-base-price');
            if (basePrice) {
                variantPriceEl.textContent = '₹' + parseFloat(basePrice).toLocaleString('en-IN');
            }
            // Hide SKU
            if (variantSkuContainer) variantSkuContainer.style.display = 'none';
        }

        // Stock badge & Add to cart button
        if (resolvedVariant) {
            if (resolvedVariant.in_stock) {
                stockBadgeEl.innerHTML = `<span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-2" style="font-size:.88rem;"><i class="fas fa-check-circle me-1"></i> In Stock (${resolvedVariant.stock_quantity})</span>`;
                addToCartBtn.disabled = false;
                addToCartBtn.innerHTML = '<i class="fa fa-shopping-bag me-2 text-white"></i> Add to cart';
            } else {
                stockBadgeEl.innerHTML = `<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-2" style="font-size:.88rem;"><i class="fas fa-times-circle me-1"></i> Out of Stock</span>`;
                addToCartBtn.disabled = true;
                addToCartBtn.innerHTML = '<i class="fa fa-ban me-2"></i> Out of Stock';
            }
        } else {
            // No variant fully resolved
             stockBadgeEl.innerHTML = `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-3 py-2" style="font-size:.88rem;"><i class="fas fa-hand-pointer me-1"></i> Select options to view stock</span>`;
             addToCartBtn.disabled = true;
             addToCartBtn.innerHTML = '<i class="fa fa-shopping-bag me-2 text-white"></i> Add to cart';
        }

        // Highlight thumbnails
        highlightGallery(avIds);

        // Persist to URL
        const params = new URLSearchParams(window.location.search);
        Object.entries(selectedAttrs).forEach(([attrName, avId]) => {
            if (avId) params.set(attrName.toLowerCase().replace(/\s+/g, '_'), avId);
            else params.delete(attrName.toLowerCase().replace(/\s+/g, '_'));
        });
        history.replaceState(null, '', window.location.pathname + (params.toString() ? '?' + params.toString() : ''));
    }

    // ── Click handlers ────────────────────────────────────────────────────────
    document.querySelectorAll('[data-av-id]').forEach(el => {
        el.addEventListener('click', function () {
            if (this.classList.contains('unavailable')) return;
            const attrName = this.dataset.attrName;
            const avId = parseInt(this.dataset.avId);
            const avValue = this.dataset.avValue;
            const labelId = 'selected-' + attrName.toLowerCase().replace(/\s+/g, '-');

            if (selectedAttrs[attrName] === avId) {
                // Deselect
                selectedAttrs[attrName] = null;
                this.classList.remove('active');
                const lbl = document.getElementById(labelId);
                if (lbl) lbl.textContent = '—';
                variantInput.value = '';
            } else {
                // Select
                document.querySelectorAll(`[data-attr-name="${attrName}"]`).forEach(e => e.classList.remove('active'));
                selectedAttrs[attrName] = avId;
                this.classList.add('active');
                const lbl = document.getElementById(labelId);
                if (lbl) lbl.textContent = avValue;
            }
            updateUI();
        });
    });

    // ── Restore from URL on page load ─────────────────────────────────────────
    (function restoreFromURL() {
        const params = new URLSearchParams(window.location.search);
        params.forEach((avIdStr) => {
            const avId = parseInt(avIdStr);
            if (!avId) return;
            const el = document.querySelector(`[data-av-id="${avId}"]`);
            if (el) el.click();
        });
    })();

    // Apply colors to swatches (to satisfy IDE CSS validators)
    document.querySelectorAll('.color-swatch-btn').forEach(btn => {
        if (btn.dataset.color) {
            btn.style.backgroundColor = btn.dataset.color;
        }
    });

})();
