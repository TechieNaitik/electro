function applyPriceFilter() {
  const maxPrice = document.getElementById("maxPriceInput").value;
  const urlParams = new URLSearchParams(window.location.search);
  if (maxPrice) {
    urlParams.set("max_price", maxPrice);
  } else {
    urlParams.delete("max_price");
  }
  window.location.search = urlParams.toString();
}

function applySort(value) {
  const urlParams = new URLSearchParams(window.location.search);
  if (value) {
    urlParams.set("sort", value);
  } else {
    urlParams.delete("sort");
  }
  window.location.search = urlParams.toString();
}
