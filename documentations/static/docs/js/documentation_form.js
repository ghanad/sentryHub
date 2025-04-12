/**
 * Checks if the text contains Persian/Arabic characters.
 * @param {string} text - The text to check.
 * @returns {boolean} - True if RTL characters are found, false otherwise.
 */
function isPersianText(text) {
    if (!text) return false;
    const rtlRegex = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
    return rtlRegex.test(text);
}

/**
 * Sets the direction and font styles for a wrapper element based on initial content.
 * Note: This might not perfectly reflect dynamic typing in TinyMCE.
 * @param {HTMLElement} wrapperElement - The wrapper element (e.g., div containing the textarea).
 * @param {string} initialContent - The initial text content to check.
 */
function setWrapperDirection(wrapperElement, initialContent) {
    if (!wrapperElement) return;
    if (isPersianText(initialContent)) {
        wrapperElement.style.direction = 'rtl';
        // Add other wrapper-specific styles if needed (less common)
        wrapperElement.classList.add('rtl-wrapper'); // For potential CSS targeting
    } else {
        wrapperElement.style.direction = ''; // Reset to default
        wrapperElement.classList.remove('rtl-wrapper');
    }
}


document.addEventListener('DOMContentLoaded', function () {
    // Initialize Bootstrap Tooltips (if any)
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // TinyMCE Initialization is primarily handled by the Django widget (`{{ form.media }}`).
    // This JS file is mostly for potential future enhancements or specific overrides
    // that need to run *after* TinyMCE is initialized.

    // Example: Attempt to set initial direction for the *wrapper* of the description field
    // This relies on accessing the original textarea's content *before* TinyMCE replaces it,
    // which might be unreliable depending on timing.
    /*
    const descriptionTextarea = document.getElementById('{{ form.description.id_for_label }}'); // Get the original textarea ID
    const descriptionWrapper = document.getElementById('description-field-wrapper');
    if (descriptionTextarea && descriptionWrapper) {
        setWrapperDirection(descriptionWrapper, descriptionTextarea.value);
    }
    */
     // A more reliable way might be to check the content *after* TinyMCE initializes,
     // but that requires hooking into TinyMCE's events (more complex).
     // For now, rely on the `directionality: 'rtl'` setting within TinyMCE's config
     // if RTL is the primary expected language for the description.

    console.log("Documentation Form JS loaded.");

    // Example of how you *might* interact with TinyMCE *after* it's loaded
    // (Requires knowing the editor ID, often the same as the textarea ID)
    /*
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            // Your *additional* TinyMCE settings specific to this page can go here,
            // potentially overriding some defaults. Or use tinymce.get('editor_id')...
            // e.g. selector: '#id_description', setup: function(editor) { ... }
        });
    }
    */
});