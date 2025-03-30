# Usage:
To automatically apply RTL layout and the IranSansX font for Persian text, add the class detect-rtl to the HTML element
directly containing
the dynamic text (e.g., <p class="detect-rtl">{{ variable }}</p>, <td class="detect-rtl">...</td>).

# Requirement:
Ensure the relevant base template (e.g., base_modern.html) loads the /static/core/js/rtl-text.js script, which performs the detection and applies the necessary styles.