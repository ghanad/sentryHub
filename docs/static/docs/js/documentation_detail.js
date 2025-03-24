document.addEventListener('DOMContentLoaded', function() {
    // Function to detect Persian text
    function isPersianText(text) {
        // Persian Unicode range: \u0600-\u06FF
        const persianRegex = /[\u0600-\u06FF]/;
        return persianRegex.test(text);
    }

    // Function to set text direction based on content
    function setTextDirection(element) {
        if (isPersianText(element.textContent)) {
            element.style.direction = 'rtl';
            element.style.textAlign = 'right';
        } else {
            element.style.direction = 'ltr';
            element.style.textAlign = 'left';
        }
    }

    // Apply RTL/LTR detection to all paragraphs in documentation content
    const documentationContent = document.querySelector('.documentation-content');
    if (documentationContent) {
        const paragraphs = documentationContent.querySelectorAll('p');
        paragraphs.forEach(setTextDirection);
    }
});
