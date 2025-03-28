# SentryHub UI/UX Modern Design Guidelines

## 1. Introduction

This document defines the UI/UX design guidelines for the SentryHub platform to ensure all parts of the application follow a modern, consistent, and user-friendly design approach. Our goal is to create a smooth, beautiful, and efficient user interface that makes system monitoring and management easier.

## 2. Core Design Principles

### 2.1. Design Philosophy

* **Purposeful Minimalism:** Use essential elements and avoid clutter. Each component should have a clear purpose.
* **Data Clarity:** Information should be presented in a way that's quickly and easily understood.
* **Visual Hierarchy:** Use visual hierarchy to guide the user's eye to the most important information.
* **Responsiveness:** All interfaces must work well across all devices from desktop to mobile.
* **Discoverability:** System capabilities should be easy to discover without cluttering the interface.

### 2.2. Design Personas

The SentryHub interface should meet the expectations of two main groups:

* **Operations Specialists:** Need to quickly review system status and identify urgent issues.
* **System Administrators:** Need detailed reports, deeper analysis, and configuration capabilities.

## 3. Design System

### 3.1. Colors

#### Primary Color Palette

```css
:root {
    --primary: #4361ee;      /* Primary color for interactive and emphasis elements */
    --primary-light: #4895ef;/* Lighter version of primary */
    --secondary: #3f37c9;    /* Secondary color for visual variety */
    --success: #2ec4b6;      /* For successful and healthy states */
    --info: #3a86ff;         /* For neutral information */
    --warning: #ff9f1c;      /* For warnings */
    --danger: #ef476f;       /* For errors and critical states */
    --dark: #1e2a38;         /* Dark color for backgrounds or text */
    --dark-blue: #0f1924;    /* Darker color for contrast */
}
```

#### Gray Scale Palette

```css
:root {
    --gray-100: #f8f9fa;
    --gray-200: #e9ecef;
    --gray-300: #dee2e6;
    --gray-400: #ced4da;
    --gray-500: #adb5bd;
    --gray-600: #6c757d;
    --gray-700: #495057;
    --gray-800: #343a40;
    --gray-900: #212529;
}
```

#### Color Usage

* **Primary Buttons:** `--primary`
* **Secondary Buttons:** `--gray-200` with `--gray-700` text
* **Action Buttons:** According to function (e.g., `--danger` for delete)
* **Status Indicators:** 
  * Critical: `--danger`
  * Warning: `--warning`
  * Info: `--info`
  * Success/Healthy: `--success`
* **Sidebar Background:** Gradient from `--dark` to `--dark-blue`
* **Main Background:** `#f5f7fa`
* **Cards & Panels:** `white`

### 3.2. Typography

#### Main Font
```css
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
```

#### Text Hierarchy
* **Page Title:** 1.75rem / 28px, weight 600
* **Card Title:** 1.125rem / 18px, weight 600
* **Body Text:** 1rem / 16px, weight 400
* **Subtitle:** 0.875rem / 14px, weight 500
* **Small Text:** 0.75rem / 12px, weight 400
* **Code & Monospace Text:** `SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace`

#### Standard Sizes and Weights
* **Heading 1 (h1):** 1.75rem, 700
* **Heading 2 (h2):** 1.5rem, 600
* **Heading 3 (h3):** 1.25rem, 600
* **Heading 4 (h4):** 1.125rem, 600
* **Heading 5 (h5):** 1rem, 600

### 3.3. Icons

Use the BoxIcons icon set. This icon collection is modern, comprehensive, and easy to implement:

```html
<link href='https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css' rel='stylesheet'>
```

#### Common Icons

* Dashboard: `bxs-dashboard`
* Alerts: `bxs-bell`
* Servers/Infrastructure: `bxs-server`
* Charts/Metrics: `bx-line-chart`
* Reports: `bxs-report`
* Settings: `bxs-cog`
* Refresh: `bx-refresh`
* Search: `bx-search`
* Filter: `bx-filter-alt`
* More/Menu: `bx-dots-vertical-rounded`
* Close: `bx-x`
* Check: `bx-check`
* Error/Critical: `bxs-error`
* Warning: `bxs-bell`
* Mute: `bxs-volume-mute`
* Success: `bxs-check-circle`

#### Icon Sizes
* Large Icon: 2rem / 32px
* Medium Icon: 1.5rem / 24px
* Small Icon: 1.25rem / 20px
* Extra Small Icon: 1rem / 16px

### 3.4. Shadows and Elevations

```css
:root {
    --box-shadow: 0 .5rem 1rem rgba(0,0,0,.08);
    --box-shadow-sm: 0 .125rem .25rem rgba(0,0,0,.05);
    --box-shadow-lg: 0 1rem 3rem rgba(0,0,0,.12);
}
```

* **Standard Shadow for Cards:** `--box-shadow`
* **Small Shadow for Buttons:** `--box-shadow-sm`
* **Large Shadow for Modals and Popups:** `--box-shadow-lg`

### 3.5. Border Radius and Edges

```css
:root {
    --border-radius: 0.5rem;      /* Standard for cards */
    --border-radius-sm: 0.25rem;  /* Small for small buttons */
    --border-radius-lg: 1rem;     /* Large for badges */
    --border-radius-pill: 50rem;  /* Pill shaped */
}
```

* **Cards & Panels:** `--border-radius`
* **Buttons:** `--border-radius`
* **Input Fields:** `--border-radius`
* **Status Badges:** `--border-radius-lg`
* **Pill Badges:** `--border-radius-pill`

### 3.6. Spacing and Sizing

```css
:root {
    --spacing-xs: 0.25rem;   /* 4px */
    --spacing-sm: 0.5rem;    /* 8px */
    --spacing-md: 1rem;      /* 16px */
    --spacing-lg: 1.5rem;    /* 24px */
    --spacing-xl: 2rem;      /* 32px */
    --spacing-xxl: 3rem;     /* 48px */
}
```

* **Card Internal Padding:** `--spacing-lg`
* **Row Spacing:** `--spacing-lg`
* **Spacing Between Sequential Items:** `--spacing-md`
* **Button Internal Padding:** `--spacing-sm` `--spacing-md`
* **Margin Between Main Sections:** `--spacing-xl`

## 4. Page Structure and Layout

### 4.1. Sidebar

Main sidebar with modern design, collapsible:

```html
<aside class="sidebar" id="sidebar">
    <div class="sidebar-header">
        <a href="#" class="sidebar-logo">
            <i class='bx bx-shield-quarter'></i>
            <span>SentryHub</span>
        </a>
        <button class="sidebar-toggle" id="sidebarToggle">
            <i class='bx bx-chevron-left'></i>
        </button>
    </div>
    
    <ul class="sidebar-nav">
        <!-- Menu items -->
        <li class="nav-item">
            <a href="#" class="nav-link active">
                <i class='bx bxs-dashboard nav-icon'></i>
                <span class="nav-text">Dashboard</span>
            </a>
        </li>
        <!-- Other items -->
    </ul>
    
    <div class="sidebar-footer">
        <!-- Sidebar footer content -->
    </div>
</aside>
```

#### Sidebar Properties
* **Width:** 260px in expanded state, 70px in collapsed state
* **Background:** Dark gradient from `--dark` to `--dark-blue`
* **Text Color:** White for active, rgba(255, 255, 255, 0.7) for inactive
* **Active Items:** `--primary` background with shadow
* **Hover:** rgba(255, 255, 255, 0.1) background

### 4.2. Main Content

```html
<main class="main-content" id="mainContent">
    <!-- Page header -->
    <header class="page-header">
        <div>
            <h1 class="page-title">Page Title</h1>
            <p class="date-display">Time information</p>
        </div>
        <div class="page-header-actions">
            <!-- Buttons and filters -->
        </div>
    </header>
    
    <!-- Main page content -->
    <div class="row g-4">
        <!-- Cards and sections -->
    </div>
</main>
```

#### Content Properties
* **Padding:** `--spacing-xl` (2rem)
* **Row Spacing:** `--spacing-lg` (1.5rem)
* **Margin from Sidebar:** 260px in expanded state, 70px in collapsed state

### 4.3. Stat Cards

```html
<div class="stat-card">
    <div class="stat-icon stat-danger">
        <i class='bx bxs-error'></i>
    </div>
    <div class="stat-value">15</div>
    <p class="stat-label">Total Firing Alerts</p>
    <div class="stat-trend trend-up">
        <i class='bx bx-up-arrow-alt'></i> 23%
    </div>
</div>
```

#### Card Properties
* **Background:** White
* **Shadow:** `--box-shadow-sm`, on hover: `--box-shadow`
* **Border Radius:** `--border-radius`
* **Padding:** `--spacing-lg`
* **Hover Effect:** Translate up with deeper shadow

### 4.4. Chart Cards

```html
<div class="chart-card">
    <div class="chart-card-header">
        <h5 class="chart-title">
            <i class='bx bx-line-chart' style="color: var(--primary)"></i>
            Chart Title
        </h5>
        <div class="chart-actions">
            <!-- Filter or action buttons -->
        </div>
    </div>
    <div class="chart-card-body">
        <div class="chart-container">
            <canvas id="myChart"></canvas>
        </div>
    </div>
</div>
```

#### Chart Card Properties
* **Header:** `--spacing-md` padding, with thin border at bottom
* **Body:** `--spacing-lg` padding
* **Chart Height:** 300px standard

### 4.5. Data Tables

```html
<table class="alert-table">
    <thead>
        <tr>
            <th>Column 1</th>
            <th>Column 2</th>
            <!-- Other columns -->
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Data 1</td>
            <td>Data 2</td>
            <!-- Other data -->
        </tr>
        <!-- Other rows -->
    </tbody>
</table>
```

#### Modern Table Properties
* **Spacing:** `border-collapse: separate; border-spacing: 0;`
* **Header:** `--gray-100` background, `--gray-700` text, small font with uppercase
* **Rows:** White background, with `--gray-100` hover
* **Cells:** `--spacing-md --spacing-lg` padding
* **Row Border Radius:** First and last cell of each row should be rounded

## 5. UI Elements

### 5.1. Buttons

#### Primary Button
```html
<button class="btn btn-primary d-flex align-items-center gap-2">
    <i class='bx bx-refresh'></i> Refresh
</button>
```

#### Secondary Button
```html
<button class="btn btn-light d-flex align-items-center gap-2">
    <i class='bx bx-calendar'></i> Select Date
</button>
```

#### Small Action Button
```html
<button class="action-btn" data-bs-toggle="tooltip" title="Acknowledge">
    <i class='bx bx-check'></i>
</button>
```

#### Danger Button
```html
<button class="btn btn-danger d-flex align-items-center gap-2">
    <i class='bx bx-trash'></i> Delete
</button>
```

### 5.2. Status Badges

```html
<span class="status-badge badge-critical">
    <i class='bx bxs-circle'></i> Critical
</span>

<span class="status-badge badge-warning">
    <i class='bx bxs-circle'></i> Warning
</span>

<span class="status-badge badge-info">
    <i class='bx bxs-circle'></i> Info
</span>

<span class="status-badge badge-success">
    <i class='bx bxs-circle'></i> Healthy
</span>
```

#### Badge Styles
```css
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-weight: 500;
    font-size: 0.75rem;
}

.badge-critical {
    background: rgba(239, 71, 111, 0.1);
    color: var(--danger);
}

.badge-warning {
    background: rgba(255, 159, 28, 0.1);
    color: var(--warning);
}

.badge-info {
    background: rgba(58, 134, 255, 0.1);
    color: var(--info);
}

.badge-success {
    background: rgba(46, 196, 182, 0.1);
    color: var(--success);
}
```

### 5.3. Input Fields and Forms

#### Search
```html
<div class="input-group">
    <span class="input-group-text bg-light border-0">
        <i class='bx bx-search'></i>
    </span>
    <input type="text" class="form-control bg-light border-0" placeholder="Search...">
</div>
```

#### Simple Input Field
```html
<div class="form-group">
    <label class="form-label">Field Title</label>
    <input type="text" class="form-control" placeholder="Placeholder text">
    <div class="form-text">Small explanatory text</div>
</div>
```

#### Dropdown Selector
```html
<div class="dropdown">
    <button class="btn btn-light dropdown-toggle d-flex align-items-center gap-2" type="button" id="dropdownMenuButton" data-bs-toggle="dropdown" aria-expanded="false">
        <i class='bx bx-calendar'></i> Select
    </button>
    <ul class="dropdown-menu" aria-labelledby="dropdownMenuButton">
        <li><a class="dropdown-item" href="#">Option 1</a></li>
        <li><a class="dropdown-item" href="#">Option 2</a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item" href="#">Option 3</a></li>
    </ul>
</div>
```

### 5.4. Charts

Using Chart.js with custom settings:

```javascript
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'bottom',
            labels: {
                usePointStyle: true,
                padding: 20,
                font: {
                    family: 'Inter',
                    size: 12
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(30, 42, 56, 0.8)',
            titleFont: {
                family: 'Inter',
                size: 13
            },
            bodyFont: {
                family: 'Inter',
                size: 12
            },
            padding: 12,
            cornerRadius: 8,
            boxPadding: 6
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            },
            ticks: {
                font: {
                    family: 'Inter',
                    size: 11
                }
            }
        },
        y: {
            grid: {
                borderDash: [3, 3],
                drawBorder: false
            },
            ticks: {
                font: {
                    family: 'Inter',
                    size: 11
                }
            }
        }
    }
};
```

#### Chart Color Palette
Chart color palette should align with the system's main colors:

* Main Line Chart: `--primary`
* Donut Chart for Statuses:
  * Critical: `--danger`
  * Warning: `--warning` 
  * Info: `--info`
  * Success/Healthy: `--success`
* Multi-section Bar Charts:
  * Primary: `--primary` 
  * Secondary: `--secondary`
  * Light Blue: `--primary-light`

## 6. Special States and Notifications

### 6.1. Loading States

```html
<div class="loading-state">
    <div class="spinner">
        <div class="spinner-ring"></div>
    </div>
    <p class="loading-text">Loading...</p>
</div>
```

```css
.loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-xl);
}

.spinner {
    width: 40px;
    height: 40px;
    position: relative;
    margin-bottom: var(--spacing-md);
}

.spinner-ring {
    position: absolute;
    width: 100%;
    height: 100%;
    border: 3px solid rgba(67, 97, 238, 0.1);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.loading-text {
    color: var(--gray-600);
    font-size: 0.875rem;
}
```

### 6.2. Empty States

```html
<div class="empty-state">
    <div class="empty-icon">
        <i class='bx bx-inbox'></i>
    </div>
    <h4 class="empty-title">No Alerts Found</h4>
    <p class="empty-description">All systems are running properly.</p>
    <button class="btn btn-primary d-flex align-items-center gap-2 mx-auto">
        <i class='bx bx-plus-circle'></i> Configure New Alert
    </button>
</div>
```

```css
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-xxl);
    text-align: center;
}

.empty-icon {
    font-size: 3rem;
    color: var(--gray-400);
    margin-bottom: var(--spacing-md);
}

.empty-title {
    font-weight: 600;
    color: var(--gray-800);
    margin-bottom: var(--spacing-sm);
}

.empty-description {
    color: var(--gray-600);
    margin-bottom: var(--spacing-lg);
    max-width: 300px;
}
```

### 6.3. Toasts & Notifications

```html
<div class="toast-container position-fixed bottom-0 end-0 p-3">
    <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="toast-header">
            <i class='bx bx-check-circle me-2 text-success'></i>
            <strong class="me-auto">Success</strong>
            <small>Just now</small>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            Changes have been saved successfully.
        </div>
    </div>
</div>
```

#### Custom Toast Styles
```css
.toast {
    background-color: white;
    border: none;
    box-shadow: var(--box-shadow);
    border-radius: var(--border-radius);
}

.toast-header {
    border-bottom: 1px solid var(--gray-200);
    background-color: white;
    font-weight: 500;
}

.toast-body {
    font-size: 0.875rem;
}
```

## 7. Interaction Guidelines

### 7.1. Animations & Transitions

```css
:root {
    --transition-fast: all 0.15s ease;
    --transition-normal: all 0.25s ease;
    --transition-slow: all 0.4s ease;
}
```

* **Button Hovers:** `--transition-fast`
* **Sidebar State Change:** `--transition-normal`
* **Card Open/Close:** `--transition-normal`
* **Element Fades:** `--transition-normal`
* **Attention-grabbing Animations:** `--transition-slow`

### 7.2. Interactive Feedback

* **Hover:** Color and shadow changes to indicate clickability
* **Focus:** Using outline with `--primary` color for keyboard accessibility
* **Active:** Deeper color and shadow changes to indicate press state
* **Loading:** Clear indication when system is processing (spinners, progress bars)
* **Success/Error:** Clear visual confirmation after user actions

### 7.3. Mobile & Responsive Behavior

* **Sidebar:** Collapses off-screen with a toggle button
* **Tables:** Scroll horizontally when needed
* **Cards:** Stack vertically on smaller screens
* **Navigation:** Simplified for mobile with drop-down menus
* **Touch Targets:** Minimum size of 44×44px for all interactive elements

## 8. Accessibility Guidelines

### 8.1. Color & Contrast

* Ensure sufficient contrast between text and background (WCAG AA: 4.5:1 for normal text, 3:1 for large text)
* Do not rely solely on color to convey information (always include text or icons)
* Provide a high contrast mode option

### 8.2. Keyboard Navigation

* All interactive elements must be focusable
* Logical tab order following the visual layout
* Visible focus indicators
* Keyboard shortcuts for common actions

### 8.3. Screen Reader Support

* Use semantic HTML elements
* Provide appropriate ARIA labels
* Include alt text for all images
* Test with screen readers

## 9. Implementation Guidelines

### 9.1. Code Structure

* Maintain separation of concerns (HTML for structure, CSS for presentation, JS for behavior)
* Use utility classes for common patterns
* Keep component-specific CSS modularized
* Document complex components

### 9.2. Performance Considerations

* Optimize image sizes
* Lazy-load content that is not immediately visible
* Minimize JavaScript execution time
* Use appropriate caching strategies

### 9.3. Browser Support

* Support the latest two versions of major browsers
* Gracefully degrade features for older browsers
* Use progressive enhancement when possible

## 10. Design Implementation Process

### 10.1. Design to Development Workflow

1. Create design mockups in Figma or similar tool
2. Export assets in appropriate formats
3. Document component specifications
4. Implement components with proper testing
5. Review implementation against design specifications

### 10.2. Design Updates

* Document all design changes
* Version control design assets
* Maintain a design system changelog
* Communicate changes to development team

## 11. Example Templates

The UI Kit includes the following basic templates to be used as starting points:

1. Dashboard
2. Alert List
3. System Details
4. Configuration Page
5. Report Page
6. Settings
7. Login/Authentication

These templates follow all the design guidelines outlined in this document and provide a consistent user experience across the application.

---

## Appendix: Implementation Checklist

Use this checklist when implementing new features or pages to ensure consistency with the design system:

- [ ] Uses the defined color palette
- [ ] Follows typography guidelines
- [ ] Includes proper spacing and layout
- [ ] Responsive on all screen sizes
- [ ] Follows accessibility guidelines
- [ ] Uses consistent icons and visual elements
- [ ] Provides appropriate loading and empty states
- [ ] Includes proper error handling and user feedback
- [ ] Optimized for performance
- [ ] Compatible with dark mode (if applicable)
