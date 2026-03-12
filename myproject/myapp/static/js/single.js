document
  .getElementById("ajax-add-to-cart-form")
  .addEventListener("submit", function (e) {
    e.preventDefault();
    const formData = new FormData(this);
    const url = this.getAttribute("action");

    fetch(url, {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          showNotification(data.message);
          updateCartHeader(data.cart_count);
        } else {
          showNotification(data.message, "error");
        }
      })
      .catch((error) => console.error("Error:", error));
  });
