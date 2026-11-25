/**
 * Antique Hub — Premier Curated Antique Marketplace
 * Core Client Experience Engine & Interactive Micro-Animations
 */

// Global namespace
window.AntiqueHub = window.AntiqueHub || {};

// Helper to retrieve CSRF token from browser cookies or DOM
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

function getCsrfToken() {
    return getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

/* ==========================================================================
   1. Global Top Loading Progress Bar Controller
   ========================================================================== */
const LoadingBar = {
    bar: null,
    timer: null,

    init: function () {
        this.bar = document.getElementById('globalLoadingBar');
        if (!this.bar) {
            this.bar = document.createElement('div');
            this.bar.id = 'globalLoadingBar';
            document.body.prepend(this.bar);
        }
    },

    start: function () {
        if (!this.bar) this.init();
        clearInterval(this.timer);
        this.bar.classList.add('active');
        this.bar.style.width = '15%';
        let progress = 15;
        this.timer = setInterval(() => {
            if (progress < 85) {
                progress += Math.random() * 12;
                this.bar.style.width = Math.min(progress, 85) + '%';
            }
        }, 200);
    },

    finish: function () {
        if (!this.bar) return;
        clearInterval(this.timer);
        this.bar.style.width = '100%';
        setTimeout(() => {
            this.bar.classList.remove('active');
            setTimeout(() => {
                this.bar.style.width = '0%';
            }, 300);
        }, 250);
    }
};
window.AntiqueHub.LoadingBar = LoadingBar;

/* ==========================================================================
   2. Luhn Algorithm for Credit/Debit Card Validation (Payments Module)
   ========================================================================== */
function validateLuhn(cardNumber) {
    const cleanNum = cardNumber.replace(/\D/g, '');
    if (cleanNum.length < 13 || cleanNum.length > 19) return false;

    let sum = 0;
    let shouldDouble = false;

    for (let i = cleanNum.length - 1; i >= 0; i--) {
        let digit = parseInt(cleanNum.charAt(i), 10);
        if (shouldDouble) {
            digit *= 2;
            if (digit > 9) digit -= 9;
        }
        sum += digit;
        shouldDouble = !shouldDouble;
    }
    return sum % 10 === 0;
}

/* ==========================================================================
   3. Universal Image Upload Preview Widget
   ========================================================================== */
function initImagePreviews() {
    const fileInputs = document.querySelectorAll('input[type="file"][accept*="image"], input[type="file"].image-preview-input, input[type="file"][name*="img"], input[type="file"][name*="image"], input[type="file"][name*="proof"]');

    fileInputs.forEach(input => {
        // Prevent duplicate initializations
        if (input.dataset.previewInitialized === 'true') return;
        input.dataset.previewInitialized = 'true';

        // Find or create preview wrapper container
        let previewWrapper = input.closest('.form-group, .mb-3, .col-12, .col-md-6, div')?.querySelector('.image-preview-wrapper');
        if (!previewWrapper) {
            previewWrapper = document.createElement('div');
            previewWrapper.className = 'image-preview-wrapper';
            input.parentNode.insertBefore(previewWrapper, input.nextSibling);
        }

        input.addEventListener('change', function () {
            // Clear existing previews
            previewWrapper.innerHTML = '';
            removeFieldError(input);

            const file = this.files && this.files[0];
            if (!file) return;

            // 1. Validate file extension / mime type
            const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg', 'image/gif'];
            const fileExt = file.name.split('.').pop().toLowerCase();
            const validExts = ['jpg', 'jpeg', 'png', 'webp', 'gif'];

            if (!validTypes.includes(file.type) && !validExts.includes(fileExt)) {
                setFieldError(input, 'Please select a valid image file (JPG, PNG, WEBP).');
                input.value = '';
                return;
            }

            // 2. Validate max size (5MB matching server-side validator)
            const maxSize = 5 * 1024 * 1024;
            if (file.size > maxSize) {
                setFieldError(input, `Image size exceeds 5MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB). Please choose a smaller image.`);
                input.value = '';
                return;
            }

            // 3. Render preview
            const reader = new FileReader();
            reader.onload = function (e) {
                const previewBox = document.createElement('div');
                previewBox.className = 'image-preview-box';

                const img = document.createElement('img');
                img.src = e.target.result;
                img.alt = 'Uploaded Artifact Preview';
                img.className = 'image-preview-thumb';

                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'image-preview-remove-btn';
                removeBtn.setAttribute('title', 'Remove image');
                removeBtn.innerHTML = '<i class="bi bi-x-lg"></i>';
                removeBtn.addEventListener('click', function (ev) {
                    ev.preventDefault();
                    ev.stopPropagation();
                    input.value = '';
                    previewWrapper.innerHTML = '';
                    removeFieldError(input);
                });

                const meta = document.createElement('div');
                meta.className = 'image-preview-meta';
                const sizeStr = file.size > 1024 * 1024 
                    ? (file.size / (1024 * 1024)).toFixed(2) + ' MB'
                    : (file.size / 1024).toFixed(1) + ' KB';
                meta.textContent = `${file.name.substring(0, 16)}... (${sizeStr})`;

                previewBox.appendChild(img);
                previewBox.appendChild(removeBtn);
                previewBox.appendChild(meta);
                previewWrapper.appendChild(previewBox);

                setFieldValid(input);
            };
            reader.readAsDataURL(file);
        });
    });
}
window.AntiqueHub.initImagePreviews = initImagePreviews;

/* ==========================================================================
   4. Validation Helpers (Error & Success UI States)
   ========================================================================== */
function setFieldError(field, message) {
    if (!field) return;
    field.classList.remove('is-valid');
    field.classList.add('is-invalid');

    // Find or create invalid-feedback element
    let feedback = field.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
    }
    feedback.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i> ${message}`;
}

function setFieldValid(field) {
    if (!field) return;
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');

    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.innerHTML = '';
    }
}

function removeFieldError(field) {
    if (!field) return;
    field.classList.remove('is-invalid');
    field.classList.remove('is-valid');
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.innerHTML = '';
    }
}

/* ==========================================================================
   5. Client-Side Field Validator Matching Server-Side Rules
   ========================================================================== */
function validateSingleField(field) {
    const name = field.name || field.id || '';
    const val = field.value !== undefined ? field.value.trim() : '';
    const type = field.type || '';

    // If required and empty
    if (field.hasAttribute('required') && !val && type !== 'file') {
        setFieldError(field, 'This field is required.');
        return false;
    }

    if (!val) {
        // Optional field is empty, don't validate further
        removeFieldError(field);
        return true;
    }

    // Phone / Mobile Validation (10 digits)
    if (name.includes('phone') || name.includes('mobile') || name === 'phone_number') {
        const phoneRegex = /^[0-9]{10}$/;
        if (!phoneRegex.test(val)) {
            setFieldError(field, 'Phone number must be exactly 10 numeric digits.');
            return false;
        }
    }

    // Email Validation
    if (type === 'email' || name.includes('email')) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(val)) {
            setFieldError(field, 'Please enter a valid email address (e.g. user@domain.com).');
            return false;
        }
    }

    // Password Confirmation Check
    if (name.includes('confirm_password') || name === 'password2') {
        const form = field.closest('form');
        const pass1 = form ? (form.querySelector('input[name="password"]') || form.querySelector('input[name="password1"]')) : null;
        if (pass1 && pass1.value !== field.value) {
            setFieldError(field, 'Passwords do not match.');
            return false;
        }
    }

    // Price Validation (Positive number > 0)
    if (name === 'price' || name === 'cur_price' || name.includes('amount')) {
        const num = parseFloat(val);
        if (isNaN(num) || num <= 0) {
            setFieldError(field, 'Price must be a valid positive amount greater than 0.');
            return false;
        }
    }

    // Stock & Quantity Validation (Integer >= 1)
    if (name === 'cur_stock' || name === 'tot_arr_stock' || name === 'stock' || name === 'quantity') {
        const intVal = parseInt(val, 10);
        if (isNaN(intVal) || intVal < 1 || val.includes('.')) {
            setFieldError(field, 'Stock or quantity must be a whole positive integer (at least 1).');
            return false;
        }
        // If updating cart quantity, check max stock if available
        const maxStock = field.getAttribute('max');
        if (maxStock && intVal > parseInt(maxStock, 10)) {
            setFieldError(field, `Quantity cannot exceed available stock (${maxStock}).`);
            return false;
        }
    }

    // Discount Percent Validation (1 to 90)
    if (name === 'percent' || name.includes('discount_percent')) {
        const pct = parseInt(val, 10);
        if (isNaN(pct) || pct < 1 || pct > 90) {
            setFieldError(field, 'Discount percentage must be an integer between 1% and 90%.');
            return false;
        }
    }

    // Date Range Validation (enddate > startdate)
    if (name === 'enddate' || name === 'end_date') {
        const form = field.closest('form');
        const startField = form ? (form.querySelector('[name="startdate"]') || form.querySelector('[name="start_date"]')) : null;
        if (startField && startField.value) {
            const startDate = new Date(startField.value);
            const endDate = new Date(val);
            if (endDate <= startDate) {
                setFieldError(field, 'End date must be strictly after the start date.');
                return false;
            }
        }
    }

    // Card Number Validation (Payments)
    if (name === 'card_number') {
        if (!validateLuhn(val)) {
            setFieldError(field, 'Invalid card number. Please check the digits.');
            return false;
        }
    }

    // Expiry Date Validation (MM/YY or MM/YYYY)
    if (name === 'expiry' || name === 'card_expiry') {
        const expiryRegex = /^(0[1-9]|1[0-2])\/?([0-9]{2}|[0-9]{4})$/;
        if (!expiryRegex.test(val)) {
            setFieldError(field, 'Enter expiration date as MM/YY.');
            return false;
        }
    }

    setFieldValid(field);
    return true;
}

/* ==========================================================================
   6. Universal Form Validation & Submit Spinner Handler
   ========================================================================== */
function initClientValidation() {
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        // Skip search-only query forms without requirements
        if (form.method.toLowerCase() === 'get' && !form.dataset.validate) return;

        // Attach live blur & input listeners on form inputs
        const inputs = form.querySelectorAll('input:not([type="hidden"]), select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => validateSingleField(input));
            input.addEventListener('input', () => {
                if (input.classList.contains('is-invalid')) {
                    validateSingleField(input);
                }
            });
        });

        // Form Submit Handler
        form.addEventListener('submit', function (e) {
            let formIsValid = true;
            let firstInvalidField = null;

            inputs.forEach(input => {
                const isValid = validateSingleField(input);
                if (!isValid) {
                    formIsValid = false;
                    if (!firstInvalidField) {
                        firstInvalidField = input;
                    }
                }
            });

            if (!formIsValid) {
                e.preventDefault();
                e.stopPropagation();
                if (firstInvalidField) {
                    firstInvalidField.focus();
                    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                return false;
            }

            // Form is valid: start loading animation on submit button and top bar
            LoadingBar.start();
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.classList.add('is-loading');
                // Auto revert button state after 15 seconds if navigation stalls
                setTimeout(() => {
                    submitBtn.classList.remove('is-loading');
                    LoadingBar.finish();
                }, 15000);
            }
        });
    });
}
window.AntiqueHub.initClientValidation = initClientValidation;

/* ==========================================================================
   7. DOMContentLoaded Master Initializer
   ========================================================================== */
document.addEventListener('DOMContentLoaded', function () {
    // Initialize top progress bar
    LoadingBar.init();

    // Auto-dismiss Django success messages after 5 seconds
    const alerts = document.querySelectorAll('.alert-success');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // Initialize Bootstrap tooltips if any
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize image preview functionality
    initImagePreviews();

    // Initialize form validation engine
    initClientValidation();

    // Universal Delegated AJAX Heart Toggle for Watchlist (Cards & Detail Page)
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.btn-ajax-watchlist');
        if (!btn) return;

        e.preventDefault();
        e.stopPropagation();

        const url = btn.dataset.url || btn.closest('form')?.action;
        const itemId = btn.dataset.itemId;
        if (!url) return;

        // Prevent rapid duplicate clicks
        btn.disabled = true;

        const csrfToken = getCsrfToken();

        fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken,
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({ ajax: '1' })
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
                return null;
            }
            if (response.status === 401 || response.status === 403) {
                window.location.href = '/accounts/login/';
                return null;
            }
            return response.json();
        })
        .then(data => {
            btn.disabled = false;
            if (!data || !data.success) return;

            // Synchronize all watchlist buttons for this item across the page
            const targetButtons = itemId 
                ? document.querySelectorAll(`.btn-ajax-watchlist[data-item-id="${itemId}"]`)
                : [btn];

            targetButtons.forEach(b => {
                const icon = b.querySelector('i');
                if (data.is_watchlisted) {
                    if (icon) {
                        icon.classList.remove('bi-heart', 'text-dark', 'text-secondary');
                        icon.classList.add('bi-heart-fill', 'text-danger');
                    }
                    b.setAttribute('title', 'Remove from Watchlist');
                    if (b.classList.contains('btn-outline-secondary')) {
                        b.classList.remove('btn-outline-secondary');
                        b.classList.add('btn-outline-danger');
                    }
                } else {
                    if (icon) {
                        icon.classList.remove('bi-heart-fill', 'text-danger');
                        icon.classList.add('bi-heart');
                        if (b.classList.contains('btn-card-watchlist')) {
                            icon.classList.add('text-dark');
                        }
                    }
                    b.setAttribute('title', 'Save to Watchlist');
                    if (b.classList.contains('btn-outline-danger')) {
                        b.classList.remove('btn-outline-danger');
                        b.classList.add('btn-outline-secondary');
                    }
                }

                // Trigger smooth micro-animation
                b.classList.add('heart-bounce');
                setTimeout(() => b.classList.remove('heart-bounce'), 400);
            });

            // Show feedback toast notification
            if (data.is_watchlisted) {
                showAntiqueToast('Artifact saved to your Collector Watchlist', '<i class="bi bi-heart-fill text-danger fs-5"></i>');
            } else {
                showAntiqueToast('Artifact removed from your Watchlist', '<i class="bi bi-heart text-accent-gold fs-5"></i>');
            }

            // Update live navbar watchlist counter badges
            const navCounters = document.querySelectorAll('.nav-watchlist-count');
            navCounters.forEach(counter => {
                if (data.watchlist_count > 0) {
                    counter.textContent = data.watchlist_count;
                    counter.classList.remove('d-none');
                } else {
                    counter.textContent = '';
                    counter.classList.add('d-none');
                }
            });
        })
        .catch(err => {
            btn.disabled = false;
            console.error('Watchlist AJAX toggle failed:', err);
        });
    });

    // =========================================================================
    // Universal Antique Toast Notification Engine
    // =========================================================================
    function showAntiqueToast(message, iconHtml = '<i class="bi bi-info-circle text-accent-gold fs-5"></i>') {
        let container = document.getElementById('antiqueToastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'antiqueToastContainer';
            container.className = 'antique-toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = 'antique-toast';
        toast.innerHTML = `${iconHtml}<span>${message}</span>`;
        container.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 400);
        }, 3200);
    }
    window.AntiqueHub.showToast = showAntiqueToast;

    // =========================================================================
    // Dynamic Navbar Elevation on Scroll & Back to Top Controller
    // =========================================================================
    const mainNavbar = document.getElementById('mainNavbar');
    const btnBackToTop = document.getElementById('btnBackToTop');

    window.addEventListener('scroll', function() {
        const scrollPos = window.scrollY || document.documentElement.scrollTop;
        
        // Navbar elevation class
        if (mainNavbar) {
            if (scrollPos > 24) {
                mainNavbar.classList.add('scrolled');
            } else {
                mainNavbar.classList.remove('scrolled');
            }
        }

        // Back to top visibility
        if (btnBackToTop) {
            if (scrollPos > 320) {
                btnBackToTop.classList.add('visible');
            } else {
                btnBackToTop.classList.remove('visible');
            }
        }
    }, { passive: true });

    if (btnBackToTop) {
        btnBackToTop.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // =========================================================================
    // Global Keyboard Shortcut: Focus Search (Ctrl + K or '/')
    // =========================================================================
    document.addEventListener('keydown', function(e) {
        // Ignore if user is already typing in an input, textarea, or contentEditable
        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        const isEditable = activeTag === 'input' || activeTag === 'textarea' || document.activeElement?.isContentEditable;

        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('globalNavSearchInput') || 
                                document.getElementById('faqSearchInput') || 
                                document.querySelector('input[name="q"]') || 
                                document.querySelector('input[name="search"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        } else if (e.key === '/' && !isEditable) {
            e.preventDefault();
            const searchInput = document.getElementById('globalNavSearchInput') || 
                                document.getElementById('faqSearchInput') || 
                                document.querySelector('input[name="q"]') || 
                                document.querySelector('input[name="search"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });
});

