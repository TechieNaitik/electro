document
  .getElementById("headerSearchBtn")
  .addEventListener("click", function () {
    var categoryId = document.getElementById("headerCategorySelect").value;
    var query = document.getElementById("headerSearchInput").value;
    var url = "{% url 'shop' %}?";

    if (categoryId != "0") {
      url += "cid=" + categoryId + "&";
    }
    if (query) {
      url += "q=" + encodeURIComponent(query);
    }
    window.location.href = url;
  });

// Add event listener for Enter key on search input
document
  .getElementById("headerSearchInput")
  .addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      document.getElementById("headerSearchBtn").click();
    }
  });
// Global AJAX Cart Helper
function showNotification(message, type = "success") {
  const container = document.getElementById("notification-container");
  const toast = document.createElement("div");
  toast.className = "toast-notify";

  // Map Django message tags to appropriate colors/icons
  if (type === "error" || type === "danger") {
    toast.style.borderLeftColor = "#dc3545";
    type = "error";
  } else if (type === "warning") {
    toast.style.borderLeftColor = "#ffc107";
  } else if (type === "info") {
    toast.style.borderLeftColor = "#0dcaf0";
  } else {
    toast.style.borderLeftColor = "#28a745";
    type = "success";
  }

  toast.innerHTML = `<div><i class="fa ${type === "success" ? "fa-check-circle text-success" : type === "error" ? "fa-exclamation-circle text-danger" : "fa-info-circle text-info"} me-2"></i> ${message}</div>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transform = "translateX(120%)";
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 500);
  }, 4000);
}

function updateCartHeader(count) {
  const headerTotal = document.getElementById("header-cart-total");
  if (headerTotal) headerTotal.innerText = count;
}

// Handle AJAX "Add to Cart" clicks
document.addEventListener("click", function (e) {
  const addToCartBtn = e.target.closest(".ajax-add-to-cart");
  if (addToCartBtn) {
    e.preventDefault();
    const url = addToCartBtn.getAttribute("href") || addToCartBtn.dataset.url;
    if (!url) return;

    fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          showNotification(data.message);
          updateCartHeader(data.cart_count);
        } else {
          showNotification(data.message, "error");
          if (data.redirect) window.location.href = data.redirect;
        }
      })
      .catch((error) => console.error("Error:", error));
  }
});

// Wishlist Toggle Logic
$(document).on("click", ".wishlist-btn", function (e) {
  e.preventDefault();
  const button = $(this);
  const productId = button.data("product-id");

  fetch(`/toggle-wishlist/${productId}/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": "{{ csrf_token }}",
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.status === "success") {
        // Update ALL heart buttons for this product across the page
        $(`.wishlist-btn[data-product-id="${productId}"]`).each(function () {
          $(this).toggleClass("wishlisted");
        });

        // If we are on the wishlist page/tab and the item was removed, remove the card/row visually
        if (
          (window.location.pathname.includes("/wishlist") ||
            window.location.search.includes("tab=wishlist")) &&
          data.action === "removed"
        ) {
          const container = button.closest(
            "tr, .col-md-6, .col-lg-4, .col-lg-6, .col-xl-3",
          );
          container.fadeOut(300, function () {
            $(this).remove();
            // Reload page to show empty state if all items are removed
            if ($(".wishlist-btn.wishlisted").length === 0) {
              window.location.reload();
            }
          });
        }

        showNotification(data.message);
      } else {
        showNotification(data.message, "error");
      }
    })
    .catch((error) => console.error("Error:", error));
});

// Auto-show Django Messages
window.addEventListener("load", function () {
  document
    .querySelectorAll("#django-messages .django-message")
    .forEach((el) => {
      showNotification(el.dataset.message, el.dataset.tags);
    });
});
