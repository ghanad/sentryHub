// main_dashboard/static/main_dashboard/js/modern_dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileToggle = document.getElementById('mobileToggle');
    const mainContent = document.getElementById('mainContent');
    const accountHeader = document.querySelector('.account-header');
    const accountMenu = document.querySelector('.account-menu');
    const accountToggle = document.querySelector('.account-toggle');
    // Get references to both theme toggle buttons
    const themeToggleExpanded = document.getElementById('themeToggleExpanded');
    const themeToggleCollapsed = document.getElementById('themeToggleCollapsed');
    const htmlElement = document.documentElement;

    // --- Sidebar Toggle & Pin ---
    function toggleSidebarClass(e) {
        // Check for long press (pin action)
        const isLongPress = e && e.timeStamp - (e.currentTarget.dataset.lastClick || 0) > 500;
        
        if (isLongPress) {
            // Toggle pin state
            const isPinned = !sidebar.classList.contains('sidebar-pinned');
            sidebar.classList.toggle('sidebar-pinned', isPinned);
            localStorage.setItem('sidebarPinned', isPinned);
            
            // Ensure sidebar stays open when pinned
            if (isPinned) {
                sidebar.classList.remove('sidebar-collapsed');
                mainContent.classList.remove('main-collapsed');
            }
        } else {
            // Normal toggle
            sidebar.classList.toggle('sidebar-collapsed');
            mainContent.classList.toggle('main-collapsed');
            // Remove pinned state when manually toggling
            if (sidebar.classList.contains('sidebar-pinned')) {
                sidebar.classList.remove('sidebar-pinned');
                localStorage.setItem('sidebarPinned', 'false');
            }
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('sidebar-collapsed'));
        }
        
        // Update last click time
        if (e) {
            e.currentTarget.dataset.lastClick = e.timeStamp;
        }
    }

     // --- Mobile Sidebar Toggle ---
     function toggleMobileSidebar() {
         sidebar.classList.toggle('sidebar-visible'); // Use a different class for mobile visibility
     }


    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebarClass);
    }

     if (mobileToggle) {
         mobileToggle.addEventListener('click', toggleMobileSidebar);
     }
 
     // Collapsed Account Menu Toggle
     const collapsedAccountIcon = document.querySelector('.account-collapsed-icon');
     const accountMenuCollapsed = document.querySelector('.account-menu-collapsed');
     
     if (collapsedAccountIcon && accountMenuCollapsed) {
         collapsedAccountIcon.addEventListener('click', function(e) {
             e.preventDefault();
             accountMenuCollapsed.style.display =
                 accountMenuCollapsed.style.display === 'flex' ? 'none' : 'flex';
         });
     }
 
     // Account Dropdown Toggle
     if (accountHeader) {
         accountHeader.addEventListener('click', function(e) {
             e.preventDefault();
             accountMenu.style.display = accountMenu.style.display === 'block' ? 'none' : 'block';
             accountToggle.style.transform = accountMenu.style.display === 'block' ? 'rotate(180deg)' : 'rotate(0)';
         });
     }
 
     // Close account menu when sidebar is collapsed
     function handleSidebarState() {
         if (sidebar.classList.contains('sidebar-collapsed') && accountMenu) {
             accountMenu.style.display = 'none';
             if (accountToggle) accountToggle.style.transform = 'rotate(0)';
         }
     }
 
     // Initial setup
     handleSidebarState();
 
     // --- Apply Initial Sidebar State ---
     // Check localStorage for desktop state
     if (window.innerWidth >= 992) {
         if (localStorage.getItem('sidebarPinned') === 'true') {
             sidebar.classList.add('sidebar-pinned');
             sidebar.classList.remove('sidebar-collapsed');
             mainContent.classList.remove('main-collapsed');
         } else if (localStorage.getItem('sidebarCollapsed') === 'true') {
             sidebar.classList.add('sidebar-collapsed');
             mainContent.classList.add('main-collapsed');
         }
         // Remove the temporary initial state class
         htmlElement.classList.remove('sidebar-is-initially-collapsed');
     }
 
     // Modified hover behavior
     sidebar.addEventListener('mouseenter', function() {
         if (this.classList.contains('sidebar-collapsed') &&
             !this.classList.contains('sidebar-pinned')) {
             this.classList.remove('sidebar-collapsed');
             this.classList.add('sidebar-hover');
             mainContent.classList.remove('main-collapsed');
         }
     });
 
     sidebar.addEventListener('mouseleave', function() {
         if (this.classList.contains('sidebar-hover') &&
             !this.classList.contains('sidebar-pinned')) {
             setTimeout(() => {
                 this.classList.add('sidebar-collapsed');
                 this.classList.remove('sidebar-hover');
                 mainContent.classList.add('main-collapsed');
             }, 300);
         }
     });
    // Ensure sidebar is hidden on mobile initially if using sidebar-visible class
     if (window.innerWidth < 992) {
         sidebar.classList.remove('sidebar-visible');
    }

    // --- Theme Toggle ---
    const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)");

    function setTheme(theme) {
        // Update the data-bs-theme attribute and local storage
        if (theme === 'dark') {
            htmlElement.setAttribute('data-bs-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            // Update visual state for BOTH toggles (dark mode = moon = not active)
            if (themeToggleExpanded) themeToggleExpanded.classList.remove('active');
            if (themeToggleCollapsed) themeToggleCollapsed.classList.remove('active');
        } else {
            htmlElement.setAttribute('data-bs-theme', 'light');
            localStorage.setItem('theme', 'light');
            // Update visual state for BOTH toggles (light mode = sun = active)
            if (themeToggleExpanded) themeToggleExpanded.classList.add('active');
            if (themeToggleCollapsed) themeToggleCollapsed.classList.add('active');
        }
    }

    function toggleTheme() {
        const currentTheme = localStorage.getItem('theme') || (prefersDarkScheme.matches ? 'dark' : 'light');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    }

    // Apply the saved theme or the system preference on initial load
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        setTheme(savedTheme);
    } else {
        setTheme(prefersDarkScheme.matches ? 'dark' : 'light');
    }

    // Add event listeners for BOTH toggle buttons
    if (themeToggleExpanded) {
        themeToggleExpanded.addEventListener('click', toggleTheme);
    }
    if (themeToggleCollapsed) {
        themeToggleCollapsed.addEventListener('click', toggleTheme);
    }

    // Listen for changes in system preference
    prefersDarkScheme.addEventListener('change', (e) => {
        // Only change if no theme is explicitly saved by the user
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });


    // --- Date/Time Update ---
    const dateElement = document.getElementById('currentDate');
    const timeElement = document.getElementById('currentTime');

    function updateDateTime() {
        const now = new Date();
        if (dateElement) {
            dateElement.textContent = now.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
        }
        if (timeElement) {
            timeElement.textContent = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
        }
    }

    updateDateTime();
    setInterval(updateDateTime, 60000); // Update every minute

    // --- Initialize Bootstrap Tooltips ---
    // Required if you use tooltips in the base or dashboard content
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    });

});
