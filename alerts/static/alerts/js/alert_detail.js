// File: /static/alerts/js/alert_detail.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Function to format duration
    function formatDuration(seconds) {
        if (seconds < 60) {
            return seconds + " seconds";
        } else if (seconds < 3600) {
            return Math.floor(seconds / 60) + " min " + (seconds % 60) + " sec";
        } else if (seconds < 86400) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return hours + " hr " + minutes + " min";
        } else {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            return days + " days " + hours + " hr";
        }
    }

    // Calculate durations for completed periods
    document.querySelectorAll('.duration').forEach(function(el) {
        const start = new Date(el.dataset.start);
        const end = new Date(el.dataset.end);
        const duration = Math.floor((end - start) / 1000); // Duration in seconds
        el.textContent = formatDuration(duration);
    });
    
    // Calculate ongoing durations
    document.querySelectorAll('.ongoing-duration').forEach(function(el) {
        const start = new Date(el.dataset.start);
        const now = new Date();
        const duration = Math.floor((now - start) / 1000); // Duration in seconds
        el.textContent = formatDuration(duration) + " (ongoing)";
        
        // Update ongoing duration every minute
        setInterval(function() {
            const currentDuration = Math.floor((new Date() - start) / 1000);
            el.textContent = formatDuration(currentDuration) + " (ongoing)";
        }, 60000);
    });
    
    // Store active tab in URL when changed
    const tabLinks = document.querySelectorAll('#alertTabs button');
    tabLinks.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function (e) {
            const tabId = e.target.getAttribute('data-bs-target').substring(1);
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('tab', tabId);
            window.history.pushState({}, '', currentUrl);
        });
    });

    // Check for tab parameter in URL on page load
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    if (tabParam) {
        const tab = document.querySelector(`button[data-bs-target="#${tabParam}"]`);
        if (tab) {
            tab.click();
        }
    }

    // COMMENT FUNCTIONALITY IS NOW MOVED TO revised-comments.js
    // THE CODE BELOW IS INTENTIONALLY DISABLED

    /*
    // Apply RTL detection to existing comments
    const commentTexts = document.querySelectorAll('.card-text');
    commentTexts.forEach(setTextDirection);

    // Add input event listener to comment textarea
    const commentTextarea = document.querySelector('#id_content');
    if (commentTextarea) {
        commentTextarea.addEventListener('input', handleInputDirection);
        // Set initial direction
        handleInputDirection({ target: commentTextarea });
    }

    // Handle comment form submission
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            formData.append('comment', 'true');
            
            fetch(window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    toastr.success("Comment added successfully.");
                    
                    // Clear the form
                    this.reset();
                    
                    // Add the new comment to the list
                    const commentsContainer = document.querySelector('.comments');
                    const newComment = document.createElement('div');
                    newComment.className = 'card mb-3';
                    newComment.innerHTML = `
                        <div class="card-header bg-light">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <strong>${data.user}</strong>
                                </div>
                                <div>
                                    <small class="text-muted">${new Date().toLocaleString()}</small>
                                </div>
                            </div>
                        </div>
                        <div class="card-body">
                            <p class="card-text">${data.content}</p>
                        </div>
                    `;
                    
                    // Insert at the beginning of the comments list
                    if (commentsContainer.firstChild) {
                        commentsContainer.insertBefore(newComment, commentsContainer.firstChild);
                    } else {
                        commentsContainer.appendChild(newComment);
                    }
                    
                    // Apply RTL detection to the new comment
                    const newCommentText = newComment.querySelector('.card-text');
                    setTextDirection(newCommentText);
                    
                    // Remove the "No comments" message if it exists
                    const noCommentsAlert = commentsContainer.querySelector('.alert-info');
                    if (noCommentsAlert) {
                        noCommentsAlert.remove();
                    }
                    
                    // Update the comment count
                    const commentCount = document.querySelector('#comments-tab .badge');
                    if (commentCount) {
                        const currentCount = parseInt(commentCount.textContent);
                        commentCount.textContent = (currentCount + 1).toString();
                    }
                } else {
                    toastr.error("Error adding comment.");
                }
            })
            .catch(error => {
                console.error('Error:', error);
                toastr.error("Error adding comment.");
            });
        });
    }
    */
});