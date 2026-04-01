document.addEventListener("click", function (e) {
  const updateBtn = e.target.closest(".ajax-update-cart");
  if (updateBtn) {
    e.preventDefault();
    const url = updateBtn.getAttribute("href");
    const cid = updateBtn.dataset.cid;

    fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          if (data.removed) {
            const row = document.getElementById(`cart-item-${cid}`);
            if (row) row.remove();
            showNotification("Item removed from cart");
            if (data.cart_count === 0) {
              location.reload(); // Show empty cart state
            }
          } else if (data.item) {
            document.getElementById(`qty-${cid}`).value = data.item.quantity;
            const itemTotal = document.getElementById(`item-total-${cid}`);
            itemTotal.dataset.basePrice = data.item.total_price;
          }

          const subtotalEl = document.getElementById("cart-subtotal");
          const shippingEl = document.getElementById("cart-shipping");
          const totalEl = document.getElementById("cart-total");

          if (subtotalEl) subtotalEl.setAttribute('data-base-price', data.subtotal);
          if (shippingEl) shippingEl.setAttribute('data-base-price', data.shipping);
          if (totalEl) totalEl.setAttribute('data-base-price', data.total);

          if (document.getElementById("shipping-calculation")) {
            document.getElementById("shipping-calculation").innerText =
              `₹100 x ${data.cart_count} items`;
          }
          
          // Trigger reactive update
          if (window.currencyManager) {
            window.currencyManager.applyRatesToDOM();
          }

          updateCartHeader(data.cart_count);
        } else {
          showNotification(data.message, "error");
        }
      })
      .catch((error) => console.error("Error:", error));
  }
});

// Coupon Logic
const applyCouponBtn = document.getElementById('apply-coupon-btn');
const removeCouponBtn = document.getElementById('remove-coupon-btn');
const couponInput = document.getElementById('coupon-code');
const couponMsg = document.getElementById('coupon-message');

if (applyCouponBtn) {
    applyCouponBtn.addEventListener('click', function() {
        const code = couponInput.value.trim();
        if (!code) {
            showCouponMsg("Please enter a code.", "text-danger");
            return;
        }

        fetch('/cart/apply-coupon/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ code: code })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification("Coupon applied successfully!", "success");
                setTimeout(() => location.reload(), 500); // Small delay to let notification show
            } else {
                showCouponMsg(data.message, "text-danger");
                showNotification(data.message, "error");
            }
        })
        .catch(error => {
            console.error("Error:", error);
            showNotification("Failed to apply coupon.", "error");
        });
    });
}

if (removeCouponBtn) {
    removeCouponBtn.addEventListener('click', function() {
        fetch('/cart/remove-coupon/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showNotification("Coupon removed.", "info");
                location.reload(); // Simplest way to reset everything for now
            }
        });
    });
}

function showCouponMsg(msg, className) {
    if (couponMsg) {
        couponMsg.innerText = msg;
        couponMsg.className = "mt-2 small " + className;
    }
}

function updateSummary(data) {
    const discountRow = document.getElementById('discount-row');
    const discountEl = document.getElementById('cart-discount');
    const totalEl = document.getElementById('cart-total');
    const label = document.getElementById('discount-label');
    const subtotalEl = document.getElementById('cart-subtotal');
    const shippingEl = document.getElementById('cart-shipping');

    if (discountRow) discountRow.style.display = 'flex';
    
    if (subtotalEl && data.subtotal) {
        subtotalEl.setAttribute('data-base-price', data.subtotal);
        subtotalEl.innerText = "₹" + data.subtotal;
    }
    
    if (shippingEl && data.shipping) {
        shippingEl.setAttribute('data-base-price', data.shipping);
        shippingEl.innerText = "₹" + data.shipping;
    }

    if (discountEl && data.discount !== undefined) {
        discountEl.setAttribute('data-base-price', data.discount);
        discountEl.innerText = (parseFloat(data.discount) > 0 ? "-₹" : "₹") + data.discount;
    }
    
    if (label && couponInput) label.innerText = `Discount (${couponInput.value.toUpperCase()})`;
    
    if (totalEl && data.new_total) {
        totalEl.setAttribute('data-base-price', data.new_total);
        totalEl.innerText = "₹" + data.new_total;
    }
    
    // Trigger reactive update for the entire page
    if (window.currencyManager) {
        window.currencyManager.applyRatesToDOM();
    }
}

function toggleCouponButtons(applied, code) {
    if (applied) {
        if (applyCouponBtn) applyCouponBtn.style.display = 'none';
        if (removeCouponBtn) removeCouponBtn.style.display = 'inline-block';
        if (couponInput) {
            couponInput.disabled = true;
            couponInput.value = code.toUpperCase();
        }
    } else {
        if (applyCouponBtn) applyCouponBtn.style.display = 'inline-block';
        if (removeCouponBtn) removeCouponBtn.style.display = 'none';
        if (couponInput) {
            couponInput.disabled = false;
            couponInput.value = '';
        }
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showNotification(msg, type = "success") {
    // Check if there's a toast container or just alert for now
    // Based on existing code, showNotification is assumed to exist elsewhere or we define a simple one
    console.log(`Notification (${type}): ${msg}`);
}

function updateCartHeader(count) {
    const headerCount = document.querySelector(".cart-count");
    if (headerCount) headerCount.innerText = count;
}
