// Product Image Gallery Logic
let currentImageIndex = 0;

function updateGalleryImage(element, imageUrl, index) {
    const mainImage = document.getElementById('main-product-image');
    if (!mainImage) return;

    // Fade out
    mainImage.style.opacity = '0.5';
    
    setTimeout(() => {
        mainImage.src = imageUrl;
        currentImageIndex = index;
        
        // Update active class
        document.querySelectorAll('.thumbnail-item').forEach(item => {
            item.classList.remove('active');
        });
        element.classList.add('active');
        
        // Fade in
        mainImage.style.opacity = '1';
        
        // Ensure thumbnail is visible in the strip
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }, 150);
}

function navigateGallery(direction) {
    const thumbs = document.querySelectorAll('.thumbnail-item');
    if (thumbs.length <= 1) return;

    let newIndex = currentImageIndex + direction;
    if (newIndex < 0) newIndex = thumbs.length - 1;
    if (newIndex >= thumbs.length) newIndex = 0;

    const nextThumb = thumbs[newIndex];
    if (nextThumb) {
        const imageUrl = nextThumb.querySelector('img').src;
        updateGalleryImage(nextThumb, imageUrl, newIndex);
    }
}

function setupSwipeGestures() {
    const mainImage = document.querySelector('.primary-image-container');
    if (!mainImage) return;

    let touchStartX = 0;
    let touchEndX = 0;

    mainImage.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    mainImage.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });

    function handleSwipe() {
        const threshold = 50; // minimum distance to be considered a swipe
        if (touchEndX < touchStartX - threshold) {
            // Swiped Left -> Next Image
            navigateGallery(1);
        }
        if (touchEndX > touchStartX + threshold) {
            // Swiped Right -> Previous Image
            navigateGallery(-1);
        }
    }
}

// Initial check to populate listeners
document.addEventListener('DOMContentLoaded', () => {
    const thumbs = document.querySelectorAll('.thumbnail-item');
    if (thumbs.length > 0) {
        // Keyboard Navigation (Left/Right arrows)
        document.addEventListener('keydown', (e) => {
            // Only navigate if we're not typing in an input/textarea
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
            
            if (e.key === 'ArrowLeft') {
                navigateGallery(-1);
            } else if (e.key === 'ArrowRight') {
                navigateGallery(1);
            }
        });

        // Swipe Gestures for Mobile
        setupSwipeGestures();

        // Handle Thumbnail Clicks (Delegated)
        document.getElementById('thumbnail-strip').addEventListener('click', (e) => {
            const item = e.target.closest('.thumbnail-item');
            if (item) {
                const url = item.dataset.thumbUrl;
                const index = parseInt(item.dataset.thumbIndex);
                updateGalleryImage(item, url, index);
            }
        });
    }

    // Initialize Color Swatches
    document.querySelectorAll('.color-swatch-btn').forEach(btn => {
        const color = btn.getAttribute('data-swatch-color');
        if (color) btn.style.backgroundColor = color;
    });
});


// Existing Add to Cart Logic
const cartForm = document.getElementById("ajax-add-to-cart-form");
if (cartForm) {
  cartForm.addEventListener("submit", function (e) {
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
}
