# Persian Font Usage Guidelines

## Font Selection
The project uses IranSansX as the primary Persian font. The font files are located in:
```
core/static/core/fonts/iransansx/
```

## Implementation

### CSS Setup
To use IranSansX font, add the following CSS rules:

```css
@font-face {
    font-family: 'IranSansX';
    src: url('core/static/core/fonts/iransansx/IRANSansX-Regular.woff2') format('woff2'),
         url('core/static/core/fonts/iransansx/IRANSansX-Regular.woff') format('woff');
    font-weight: 400;
    font-style: normal;
}

@font-face {
    font-family: 'IranSansX';
    src: url('core/static/core/fonts/iransansx/IRANSansX-Bold.woff2') format('woff2'),
         url('core/static/core/fonts/iransansx/IRANSansX-Bold.woff') format('woff');
    font-weight: 700;
    font-style: normal;
}
```

### Applying the Font
For Persian text content, use:

```css
.persian-text {
    font-family: 'IranSansX', system-ui, -apple-system, 'Segoe UI', Tahoma, Arial, sans-serif;
    font-weight: 400;
    line-height: 1.8;
    letter-spacing: 0;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-feature-settings: "ss01", "ss02", "ss03", "ss04";
}
```

## RTL Layout Considerations

### Text Direction
For Persian content, always set:
```css
direction: rtl;
text-align: right;
```

### Exceptions
For code blocks and pre elements, maintain LTR:
```css
pre, code {
    direction: ltr;
    text-align: left;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
```

### Tables
Tables should maintain their structure regardless of text direction:
```css
table {
    direction: ltr;
    text-align: left;
}
```

## Best Practices

1. Always use IranSansX for Persian text
2. Maintain proper RTL/LTR direction for different content types
3. Use appropriate line-height and letter-spacing for better readability
4. Ensure proper font-weight usage (400 for normal, 700 for bold)
5. Test font rendering across different browsers and devices
