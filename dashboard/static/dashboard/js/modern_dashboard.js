// main_dashboard/static/main_dashboard/js/modern_dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileToggle = document.getElementById('mobileToggle');
    const mainContent = document.getElementById('mainContent');
    const accountHeader = document.querySelector('.account-header');
    const accountMenu = document.querySelector('.account-menu');
    const accountToggle = document.querySelector('.account-toggle');
    const themeToggleExpanded = document.getElementById('themeToggleExpanded');
    const themeToggleCollapsed = document.getElementById('themeToggleCollapsed');
    const htmlElement = document.documentElement;

    // --- Sidebar Toggle & Pin ---
    // Get a reference to the icon element within the toggle button
    const toggleIcon = sidebarToggle ? sidebarToggle.querySelector('i') : null;

    function toggleSidebarClass(e) {
        if (!e || !e.currentTarget) return; // Guard against potential errors

        // Get the timestamp of the *previous* click, parsing it as a float
        const lastClickTime = parseFloat(e.currentTarget.dataset.lastClick || '0');
        const currentTime = e.timeStamp;
        let isLongPress = false;

        // Only calculate long press if it's *not* the very first click
        if (lastClickTime > 0) {
            isLongPress = (currentTime - lastClickTime) > 500; // 500ms threshold for long press
        }

        const currentlyPinned = sidebar.classList.contains('sidebar-pinned');

        // --- Logic for Pinning (Long Press) or Unpinning (Any Click when Pinned) ---
        if (currentlyPinned) {
            // If currently pinned, ANY click unpins
            sidebar.classList.remove('sidebar-pinned');
            localStorage.setItem('sidebarPinned', 'false'); // Store as string
            if (toggleIcon) {
                toggleIcon.classList.remove('bxs-pin');
                toggleIcon.classList.add('bx-pin');
            }
            if (sidebarToggle) {
                sidebarToggle.title = "Toggle Sidebar (Hold to Pin)";
            }
            // Do NOT toggle collapsed state here; let the user collapse separately if they want.
        } else {
            // If not currently pinned, check for long press to pin or short press to toggle collapse
            if (isLongPress) {
                // --- Logic for Pinning (Long Press) ---
                sidebar.classList.add('sidebar-pinned');
                sidebar.classList.remove('sidebar-collapsed'); // Ensure not collapsed if pinned
                mainContent.classList.remove('main-collapsed');
                localStorage.setItem('sidebarPinned', 'true'); // Store as string
                if (toggleIcon) {
                    toggleIcon.classList.remove('bx-pin');
                    toggleIcon.classList.add('bxs-pin');
                }
                if (sidebarToggle) {
                    sidebarToggle.title = "Unpin Sidebar";
                }
                sidebar.classList.remove('sidebar-hover'); // Remove hover state if pinning while hovered

            } else {
                // --- Logic for Toggling Collapse/Expand (Short Press) ---
                sidebar.classList.toggle('sidebar-collapsed');
                mainContent.classList.toggle('main-collapsed');

                // Store the collapsed state
                localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('sidebar-collapsed') ? 'true' : 'false'); // Store as string

                // Ensure icon remains outline pin and title remains the same
                if (toggleIcon) {
                     toggleIcon.classList.remove('bxs-pin');
                     toggleIcon.classList.add('bx-pin');
                }
                 if (sidebarToggle) {
                    sidebarToggle.title = "Toggle Sidebar (Hold to Pin)";
                }

                // Remove hover class if collapsing via click
                sidebar.classList.remove('sidebar-hover');
            }
        }


        // Update last click time at the VERY END for the next calculation
        e.currentTarget.dataset.lastClick = currentTime;
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
            if (accountMenu) {
                accountMenu.style.display = accountMenu.style.display === 'block' ? 'none' : 'block';
            }
            if (accountToggle) {
                accountToggle.style.transform = (accountMenu && accountMenu.style.display === 'block') ? 'rotate(180deg)' : 'rotate(0)';
            }
        });
    }

    // Close account menu when sidebar is collapsed (Helper for initial state)
    function handleSidebarState() {
        if (sidebar.classList.contains('sidebar-collapsed') && accountMenu) {
            accountMenu.style.display = 'none';
            if (accountToggle) accountToggle.style.transform = 'rotate(0)';
        }
    }

    // Initial setup for account menu display
    handleSidebarState();

    // --- Apply Initial Sidebar State ---
    // Check localStorage for desktop state
    // --- Apply Initial Sidebar State ---
    // Check localStorage for desktop state
    if (window.innerWidth >= 992) {
        const storedPinned = localStorage.getItem('sidebarPinned');
        const storedCollapsed = localStorage.getItem('sidebarCollapsed');

        if (storedPinned === 'true') {
            sidebar.classList.add('sidebar-pinned');
            sidebar.classList.remove('sidebar-collapsed'); // Ensure not collapsed if pinned
            mainContent.classList.remove('main-collapsed');
            if (toggleIcon) {
                toggleIcon.classList.remove('bx-pin');
                toggleIcon.classList.add('bxs-pin');
            }
            if (sidebarToggle) {
                sidebarToggle.title = "Unpin Sidebar";
            }
        } else if (storedCollapsed === 'true') {
            sidebar.classList.add('sidebar-collapsed');
            mainContent.classList.add('main-collapsed');
            sidebar.classList.remove('sidebar-pinned'); // Ensure not pinned if collapsed
             if (toggleIcon) {
                toggleIcon.classList.remove('bxs-pin');
                toggleIcon.classList.add('bx-pin');
            }
             if (sidebarToggle) {
                sidebarToggle.title = "Toggle Sidebar (Hold to Pin)";
            }
        } else {
            // Default state if nothing is stored (e.g., first visit)
             sidebar.classList.remove('sidebar-collapsed');
             mainContent.classList.remove('main-collapsed');
             sidebar.classList.remove('sidebar-pinned');
             if (toggleIcon) {
                toggleIcon.classList.remove('bxs-pin');
                toggleIcon.classList.add('bx-pin');
            }
             if (sidebarToggle) {
                sidebarToggle.title = "Toggle Sidebar (Hold to Pin)";
            }
        }
        // Remove the temporary initial state class after applying stored state
        htmlElement.classList.remove('sidebar-is-initially-collapsed');
    } else {
         // Ensure sidebar is hidden on mobile initially
         sidebar.classList.remove('sidebar-visible');
         // Remove temporary class on mobile too
         htmlElement.classList.remove('sidebar-is-initially-collapsed');
    }

    // Modified hover behavior (only applies if NOT pinned)
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
            // Use a short delay to avoid accidentally closing when moving mouse quickly
            setTimeout(() => {
                 // Double-check if still hovering before collapsing
                 if (!sidebar.matches(':hover') && this.classList.contains('sidebar-hover')) {
                     this.classList.add('sidebar-collapsed');
                     this.classList.remove('sidebar-hover');
                     mainContent.classList.add('main-collapsed');
                 }
            }, 300); // 300ms delay
        }
    });


    // --- Theme Toggle ---
    const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)");

    function setTheme(theme) {
        if (theme === 'dark') {
            htmlElement.setAttribute('data-bs-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            if (themeToggleExpanded) themeToggleExpanded.classList.remove('active');
            if (themeToggleCollapsed) themeToggleCollapsed.classList.remove('active');
        } else {
            htmlElement.setAttribute('data-bs-theme', 'light');
            localStorage.setItem('theme', 'light');
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
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    });

});