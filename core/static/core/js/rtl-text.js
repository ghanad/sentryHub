// RTL text support
function isPersianText(text) {
    // Persian Unicode range: \u0600-\u06FF
    // Arabic Unicode range: \u0750-\u077F
    // Arabic Supplement range: \u0870-\u089F
    // Arabic Extended-A range: \u08A0-\u08FF
    // Arabic Presentation Forms-A: \uFB50-\uFDFF
    // Arabic Presentation Forms-B: \uFE70-\uFEFF
    const rtlRegex = /[\u0600-\u06FF\u0750-\u077F\u0870-\u089F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
    return rtlRegex.test(text);
}

function setTextDirection(element) {
    if (isPersianText(element.textContent)) {
        element.style.direction = 'rtl';
        element.style.textAlign = 'right';
        element.style.fontFamily = "'IranSansX', system-ui, -apple-system, 'Segoe UI', Tahoma, Arial, sans-serif";
        element.style.fontWeight = '400';
        element.style.lineHeight = '1.8';
        element.style.letterSpacing = '0';
        element.style.textRendering = 'optimizeLegibility';
        element.style.webkitFontSmoothing = 'antialiased';
        element.style.mozOsxFontSmoothing = 'grayscale';
        element.style.fontFeatureSettings = '"ss01", "ss02", "ss03", "ss04"';
        element.classList.add('rtl-text');
    } else {
        element.style.direction = 'ltr';
        element.style.textAlign = 'left';
        element.style.fontFamily = '';
        element.style.fontWeight = '';
        element.style.lineHeight = '';
        element.style.letterSpacing = '';
        element.style.textRendering = '';
        element.style.webkitFontSmoothing = '';
        element.style.mozOsxFontSmoothing = '';
        element.style.fontFeatureSettings = '';
        element.classList.remove('rtl-text');
    }
}

function handleInputDirection(textarea) {
    if (isPersianText(textarea.value)) {
        textarea.style.direction = 'rtl';
        textarea.style.textAlign = 'right';
        textarea.style.fontFamily = "'IranSansX', system-ui, -apple-system, 'Segoe UI', Tahoma, Arial, sans-serif";
        textarea.style.fontWeight = '400';
        textarea.style.lineHeight = '1.8';
        textarea.style.letterSpacing = '0';
        textarea.style.textRendering = 'optimizeLegibility';
        textarea.style.webkitFontSmoothing = 'antialiased';
        textarea.style.mozOsxFontSmoothing = 'grayscale';
        textarea.style.fontFeatureSettings = '"ss01", "ss02", "ss03", "ss04"';
        textarea.classList.add('rtl-text');
    } else {
        textarea.style.direction = 'ltr';
        textarea.style.textAlign = 'left';
        textarea.style.fontFamily = '';
        textarea.style.fontWeight = '';
        textarea.style.lineHeight = '';
        textarea.style.letterSpacing = '';
        textarea.style.textRendering = '';
        textarea.style.webkitFontSmoothing = '';
        textarea.style.mozOsxFontSmoothing = '';
        textarea.style.fontFeatureSettings = '';
        textarea.classList.remove('rtl-text');
    }
}

// Initialize RTL detection for elements with data-rtl="true" attribute
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-rtl="true"]').forEach(setTextDirection);
}); 