// main_dashboard/static/main_dashboard/js/modern_dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileToggle = document.getElementById('mobileToggle');
    const mainContent = document.getElementById('mainContent');
    // const themeToggle = document.getElementById('themeToggle'); // Keep commented
    // const htmlElement = document.documentElement; // Keep commented

    // --- Sidebar Toggle ---
    function toggleSidebarClass() {
        sidebar.classList.toggle('sidebar-collapsed');
        mainContent.classList.toggle('main-collapsed');
        // Store state in localStorage
        localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('sidebar-collapsed'));
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

    // --- Apply Initial Sidebar State ---
    // Check localStorage for desktop state
    if (window.innerWidth >= 992 && localStorage.getItem('sidebarCollapsed') === 'true') {
        sidebar.classList.add('sidebar-collapsed');
        mainContent.classList.add('main-collapsed');
    }
    // Ensure sidebar is hidden on mobile initially if using sidebar-visible class
     if (window.innerWidth < 992) {
         sidebar.classList.remove('sidebar-visible');
    }

    // --- Theme Toggle (Removed) ---
    // Logic related to theme toggle, setTheme, toggleTheme, and event listener removed.

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
