document.addEventListener('DOMContentLoaded', function() {
    const checkoutForm = document.querySelector('form');
    if (!checkoutForm) return;

    const submitButton = document.getElementById('submit-button');
    const buttonText = document.getElementById('button-text');
    const spinner = document.getElementById('spinner');
    const paymentMethodRadios = document.getElementsByName('payment_method');
    
    // Read from dataset for CSRF and URLs
    const createOrderUrl = checkoutForm.getAttribute('data-create-order-url');
    const verifyPaymentUrl = checkoutForm.getAttribute('data-verify-payment-url');
    const paymentSuccessUrlBase = checkoutForm.getAttribute('data-payment-success-url');
    const csrfTokenElement = checkoutForm.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfTokenElement ? csrfTokenElement.value : '';

    function handlePaymentMethodChange() {
        const selectedRadio = document.querySelector('input[name="payment_method"]:checked');
        if (!selectedRadio) return;
        
        const selectedMethod = selectedRadio.value;
        if (selectedMethod === 'Razorpay') {
            buttonText.innerText = "Pay and Place Order";
        } else {
            buttonText.innerText = "Place Order";
        }
    }

    paymentMethodRadios.forEach(radio => {
        radio.addEventListener('change', handlePaymentMethodChange);
    });

    checkoutForm.addEventListener('submit', async function(e) {
        const selectedRadio = document.querySelector('input[name="payment_method"]:checked');
        if (!selectedRadio) return;
        
        const selectedMethod = selectedRadio.value;
        setLoading(true);

        if (selectedMethod !== 'Razorpay') {
            // Standard form submission for COD or other methods
            return;
        }

        e.preventDefault();

        try {
            // 1. Create Razorpay Order on server
            const response = await fetch(createOrderUrl, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
            });
            const orderData = await response.json();

            if (orderData.status === 'error') {
                throw new Error(orderData.message);
            }

            // 2. Open Razorpay Checkout Modal
            const options = {
                "key": orderData.key_id,
                "amount": orderData.amount,
                "currency": orderData.currency,
                "name": "Electro Store",
                "description": "Payment for your order",
                "order_id": orderData.order_id,
                "handler": function (response) {
                    // 3. Handle successful payment
                    verifyPayment(response, orderData.order_id);
                },
                "prefill": {
                    "name": orderData.customer_name,
                    "email": orderData.customer_email,
                    "contact": orderData.customer_phone
                },
                "theme": {
                    "color": "#81c408" // Match Electro theme color
                },
                "modal": {
                    "ondismiss": function() {
                        setLoading(false);
                    }
                }
            };
            const rzp = new Razorpay(options);
            rzp.open();
            
        } catch (err) {
            console.error(err);
            showMessage(err.message || "Failed to initialize payment.");
            setLoading(false);
        }
    });

    async function verifyPayment(paymentResponse, razorpayOrderId) {
        const orderNotesElement = document.getElementsByName('order_notes')[0];
        const orderNotes = orderNotesElement ? orderNotesElement.value : '';
        
        try {
            const response = await fetch(verifyPaymentUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
                body: JSON.stringify({
                    razorpay_order_id: razorpayOrderId,
                    razorpay_payment_id: paymentResponse.razorpay_payment_id,
                    razorpay_signature: paymentResponse.razorpay_signature,
                    order_notes: orderNotes
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                window.location.href = paymentSuccessUrlBase + "?order_id=" + result.order_id;
            } else {
                showMessage(result.message || "Payment verification failed.");
                setLoading(false);
            }
        } catch (e) {
            console.error(e);
            showMessage("Error verifying payment.");
            setLoading(false);
        }
    }

    // UI Helpers
    function showMessage(messageText) {
        const messageContainer = document.querySelector("#payment-message");
        if (!messageContainer) return;
        
        messageContainer.style.display = "block";
        messageContainer.textContent = messageText;

        setTimeout(function () {
            messageContainer.style.display = "none";
            messageContainer.textContent = "";
        }, 6000);
    }

    function setLoading(isLoading) {
        if (!submitButton) return;
        
        if (isLoading) {
            submitButton.disabled = true;
            if (spinner) spinner.style.display = "inline-block";
            buttonText.innerText = "Processing...";
        } else {
            submitButton.disabled = false;
            if (spinner) spinner.style.display = "none";
            const selectedRadio = document.querySelector('input[name="payment_method"]:checked');
            const selectedMethod = selectedRadio ? selectedRadio.value : '';
            buttonText.innerText = selectedMethod === 'Razorpay' ? "Pay and Place Order" : "Place Order";
        }
    }
});
