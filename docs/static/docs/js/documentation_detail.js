// docs/static/docs/js/documentation_detail.js

/**
 * Checks if the text contains Persian/Arabic characters.
 * @param {string} text - The text to check.
 * @returns {boolean} - True if RTL characters are found, false otherwise.
 */
function isPersianText(text) {
    if (!text) return false;
    // Enhanced regex to cover more RTL characters
    const rtlRegex = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
    // Check percentage of RTL characters if needed, but regex test is often enough
    return rtlRegex.test(text);
}

/**
 * Sets the direction and font styles for an element based on its text content.
 * @param {HTMLElement} element - The element to style.
 */
function setTextDirection(element) {
    if (!element) return;
    const text = element.textContent;
    if (isPersianText(text)) {
        element.style.direction = 'rtl';
        element.style.textAlign = 'right';
        element.style.direction = 'rtl';
        element.style.textAlign = 'right';
        element.classList.add('rtl-text');
    } else {
        // Reset to default LTR styles if needed (or rely on CSS defaults)
        element.style.direction = ''; // Reset to default (usually ltr)
        element.style.textAlign = ''; // Reset to default (usually left)
        element.style.fontFamily = ''; // Reset to default body font
        element.style.fontWeight = '';
        element.style.lineHeight = '';
        element.style.letterSpacing = '';
        // Reset optional optimizations
        // element.style.textRendering = '';
        // element.style.webkitFontSmoothing = '';
        // element.style.mozOsxFontSmoothing = '';
        // element.style.fontFeatureSettings = '';
        element.classList.remove('rtl-text');
    }
}


document.addEventListener('DOMContentLoaded', function () {
    // Initialize Bootstrap Tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Apply RTL/LTR detection to the main description content
    const descriptionElement = document.getElementById('description-content');
    if (descriptionElement) {
        // Select all relevant block-level children
        const blockElements = descriptionElement.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, blockquote, div');

        blockElements.forEach(element => {
            const dirAttribute = element.getAttribute('dir');
            if (dirAttribute === 'rtl') {
                element.style.direction = 'rtl';
                element.style.textAlign = 'right';
                element.classList.add('rtl-text');
            } else if (dirAttribute === 'ltr') {
                element.style.direction = 'ltr';
                element.style.textAlign = 'left';
                element.classList.remove('rtl-text');
            } else {
                // Fallback to setTextDirection if no explicit dir attribute
                setTextDirection(element);
            }
        });
    }

    // Add confirmation for unlink buttons (using event delegation)
    const linkedAlertsCard = document.querySelector('.linked-alerts-card');
    if (linkedAlertsCard) {
        linkedAlertsCard.addEventListener('submit', function(event) {
            if (event.target.classList.contains('unlink-form')) {
                const alertName = event.target.closest('tr').querySelector('.alert-name-link')?.textContent || 'this alert';
                if (!confirm(`Are you sure you want to unlink "${alertName}" from this documentation?`)) {
                    event.preventDefault(); // Stop form submission
                }
                // If confirmed, the form will submit normally via POST
            }
        });
    }


    console.log("Documentation Detail JS loaded.");
});
