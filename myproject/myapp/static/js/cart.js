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

          if (subtotalEl) subtotalEl.dataset.basePrice = data.subtotal;
          if (shippingEl) shippingEl.dataset.basePrice = data.shipping;
          if (totalEl) totalEl.dataset.basePrice = data.total;

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
