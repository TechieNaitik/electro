document
  .getElementById("headerSearchBtn")
  .addEventListener("click", function () {
    var categoryId = document.getElementById("headerCategorySelect").value;
    var query = document.getElementById("headerSearchInput").value;
    var shopUrl = this.getAttribute("data-url") || "/shop/";
    var url = shopUrl + "?";

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
  const csrftoken = document
    .querySelector('meta[name="csrf-token"]')
    ?.getAttribute("content");

  fetch(`/toggle-wishlist/${productId}/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrftoken,
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

// Universal Rating System Logic
function updateRatingDisplay(productId, average, totalVotes, alreadyVoted) {
  // Update ALL rating containers for this product (display logic only)
  $(`.rating-readonly[data-product-id="${productId}"], .rating-interactive[data-product-id="${productId}"]`).each(function () {
    const container = $(this);
    const roundedAvg = Math.round(average);

    // If it's the interactive one, we only update icons if user hasn't voted yet
    // Actually, it's better to show current average as default
    container.find("i.fa-star").each(function (index) {
      const val = index + 1;
      if (val <= roundedAvg) {
        $(this).removeClass("far").addClass("fas");
      } else {
        $(this).removeClass("fas").addClass("far");
      }
    });

    if (alreadyVoted) {
      container.addClass("voted-locked");
      container.attr("title", `You already rated this. Avg: ${average} (${totalVotes} votes)`);
    } else {
      container.attr("title", `Average Rating: ${average} (${totalVotes} votes)`);
    }
  });
}

// Initial Fetch of Ratings
function loadRatings() {
  const pids = new Set();
  $("[data-product-id]").filter(".rating-readonly, .rating-interactive").each(function () {
    pids.add($(this).data("product-id"));
  });

  pids.forEach((pid) => {
    fetch(`/api/ratings/${pid}/`)
      .then((res) => res.json())
      .then((data) => {
        updateRatingDisplay(pid, data.average, data.total_votes, data.already_voted);
      })
      .catch((err) => console.error("Error loading ratings:", err));
  });
}

// 1. Interactive Star Clicking (Only for Interactive Containers)
$(document).on("click", ".rating-interactive .star-link", function (e) {
  e.preventDefault();
  const star = $(this);
  const ratingContainer = star.closest(".rating-interactive");
  
  if (ratingContainer.hasClass("voted-locked")) {
    showNotification("You have already reviewed this product!", "info");
    return;
  }

  const val = star.data("value");
  $("#selected-rating").val(val);

  // Visual feedback for selection
  ratingContainer.find("i.fa-star").each(function (index) {
    if (index + 1 <= val) {
      $(this).removeClass("far").addClass("fas");
    } else {
      $(this).removeClass("fas").addClass("far");
    }
  });
});

// 2. Comprehensive Review Submission (Single Page)
$(document).on("submit", "#review-form", function (e) {
  e.preventDefault();
  const form = $(this);
  const ratingContainer = form.find(".rating-interactive");
  const productId = ratingContainer.data("product-id");
  const ratingValue = $("#selected-rating").val();
  const reviewText = $("#review-text").val();
  const name = form.find('input[placeholder*="Name"]').val();
  const email = form.find('input[placeholder*="Email"]').val();

  if (!ratingValue) {
    showNotification("Please select a star rating!", "error");
    return;
  }

  if (!reviewText.trim()) {
      showNotification("Please write a review comment!", "error");
      return;
  }

  const csrftoken = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");

  fetch(`/api/ratings/submit/${productId}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrftoken,
    },
    body: JSON.stringify({
        rating: ratingValue,
        review_text: reviewText,
        name: name,
        email: email
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status === "success") {
        updateRatingDisplay(productId, data.average, data.total_votes, true);
        showNotification(data.message);
        form.fadeOut(300, function() {
            $(this).replaceWith('<div class="alert alert-success">Thank you for your review!</div>');
        });
      } else {
        showNotification(data.message, "error");
      }
    })
    .catch((err) => {
      console.error("Error submitting review:", err);
      showNotification("Failed to submit review. Please try again.", "error");
    });
});

// Hover Effect for Interactive Stars
$(document)
  .on("mouseenter", ".rating-interactive .star-link", function () {
    const star = $(this);
    const ratingContainer = star.closest(".rating-interactive");
    if (ratingContainer.hasClass("voted-locked")) return;

    const ratingValue = star.data("value");
    ratingContainer.find("i.fa-star").each(function (index) {
      if (index + 1 <= ratingValue) {
        $(this).addClass("star-hover");
      }
    });
  })
  .on("mouseleave", ".rating-interactive .star-link", function () {
    $(this).closest(".rating-interactive").find("i").removeClass("star-hover");
  });

// Auto-show Django Messages and Load Ratings
window.addEventListener("load", function () {
  loadRatings();
  document
    .querySelectorAll("#django-messages .django-message")
    .forEach((el) => {
      showNotification(el.dataset.message, el.dataset.tags);
    });
});
