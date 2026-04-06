(function () {
    'use strict';

    const PRODUCT_ID    = window.PRODUCT_ID;
    const ALL_VARIANTS  = window.ALL_VARIANTS;
    const ORIGINAL_GALLERY = window.ORIGINAL_GALLERY;

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
    function swapGallery(images) {
        if (!images || !images.length) return;
        mainImg.classList.add('img-crossfade-out');
        setTimeout(() => {
            mainImg.src = images[0].url;
            mainImg.alt = images[0].alt || '';
            mainImg.classList.remove('img-crossfade-out');
        }, 300);

        if (!thumbStrip) return;
        thumbStrip.innerHTML = '';
        images.forEach((img, idx) => {
            const div = document.createElement('div');
            div.className = 'thumbnail-item border rounded bg-light cursor-pointer' + (idx === 0 ? ' active' : '');
            div.style.cssText = 'min-width:80px;width:80px;height:80px;overflow:hidden;';
            div.innerHTML = `<img src="${img.url}" class="img-fluid w-100 h-100" style="object-fit:cover;" alt="${img.alt || 'thumbnail'}" loading="lazy">`;
            
            div.addEventListener('click', () => {
                thumbStrip.querySelectorAll('.thumbnail-item').forEach(t => t.classList.remove('active'));
                div.classList.add('active');
                mainImg.classList.add('img-crossfade-out');
                setTimeout(() => { mainImg.src = img.url; mainImg.classList.remove('img-crossfade-out'); }, 300);

                // CONNECTION: If this thumbnail belongs to a variant, select its attributes
                const matchingV = ALL_VARIANTS.find(v => v.featured_image === img.url);
                if (matchingV) {
                    matchingV.attribute_ids.forEach(avId => {
                        const el = document.querySelector(`[data-av-id="${avId}"]`);
                        if (el && !el.classList.contains('active')) {
                            // Only click if it's a "Color" attribute to avoid over-selecting
                            if (el.dataset.attrName === 'Color') el.click();
                        }
                    });
                }
            });
            thumbStrip.appendChild(div);
        });
    }

    function getMatchingVariants(avIds) {
        return ALL_VARIANTS.filter(v => avIds.every(id => v.attribute_ids.includes(id)));
    }

    // ── Main UI update ────────────────────────────────────────────────────────
    function updateUI() {
        const avIds = Object.values(selectedAttrs).filter(Boolean);
        const matching = getMatchingVariants(avIds);

        // Grey out unavailable combinations
        document.querySelectorAll('[data-av-id]').forEach(el => {
            const avId = parseInt(el.dataset.avId);
            const attrName = el.dataset.attrName;
            const otherIds = Object.entries(selectedAttrs)
                .filter(([k]) => k !== attrName)
                .map(([, v]) => v).filter(Boolean);
            const viable = ALL_VARIANTS.some(v =>
                [...otherIds, avId].every(id => v.attribute_ids.includes(id))
            );
            el.classList.toggle('unavailable', !viable);
        });

        const resolvedVariant = matching.length === 1 ? matching[0] : null;

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
        }

        // Gallery swap via AJAX (Trigger on any selection to show representational images)
        if (avIds.length > 0) {
            // INSTANT SWAP: Find first matching variant in client-side data and swap main image immediately
            const instantMatch = matching.length > 0 ? matching[0] : ALL_VARIANTS.find(v => avIds.some(id => v.attribute_ids.includes(id)));
            if (instantMatch && instantMatch.featured_image) {
                // Don't swapGallery here as that clears thumbnails, just update the main image
                mainImg.classList.add('img-crossfade-out');
                setTimeout(() => {
                    mainImg.src = instantMatch.featured_image;
                    mainImg.classList.remove('img-crossfade-out');
                }, 300);
            }

            fetch(`/api/variant-options/?product_id=${PRODUCT_ID}&av_ids=${avIds.join(',')}`)
                .then(r => r.json())
                .then(data => {
                    // Use featured_gallery from partial selection if selected_variant is fully resolving yet
                    const galleryToUse = data.featured_gallery || (data.selected_variant ? data.selected_variant.gallery : null);
                    if (galleryToUse && galleryToUse.length > 0) {
                        swapGallery(galleryToUse);
                    }
                })
                .catch(() => {});
        } else {
            // Return to default gallery if nothing is selected
             swapGallery(ORIGINAL_GALLERY);
        }

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
