// Function to handle comment submission
function submitComment(alertId) {
    const commentForm = document.getElementById(`comment-form-${alertId}`);
    const commentText = document.getElementById(`comment-text-${alertId}`).value;
    
    if (!commentText.trim()) {
        SentryNotification.warning('Please enter a comment before submitting.');
        return;
    }

    // Get CSRF token from cookie
    const csrftoken = getCookie('csrftoken');

    // Send the comment to the server
    fetch(`/alerts/${alertId}/add-comment/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            text: commentText
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Clear the comment input
            document.getElementById(`comment-text-${alertId}`).value = '';
            
            // Check if we're on the first page before attempting to add the comment to the UI
            const urlParams = new URLSearchParams(window.location.search);
            const currentPage = parseInt(urlParams.get('comments_page') || '1');
            
            if (currentPage === 1) {
                // Add the new comment to the list
                const commentsList = document.getElementById(`comments-list-${alertId}`);
                const newComment = createCommentElement(data.comment);
                commentsList.insertBefore(newComment, commentsList.firstChild);
                
                // Update comment count
                const commentCountElement = document.getElementById('comments-count');
                if (commentCountElement) {
                    const currentCount = parseInt(commentCountElement.textContent);
                    commentCountElement.textContent = (currentCount + 1).toString();
                }
                
                // Show success notification
                SentryNotification.success('Comment added successfully.');
            } else {
                // If we're not on page 1, offer to navigate there to see the new comment
                const viewNewCommentLink = document.createElement('div');
                viewNewCommentLink.className = 'alert alert-info mt-3';
                viewNewCommentLink.innerHTML = `
                    <p class="mb-0">Your comment was added successfully. 
                    <a href="?fingerprint=${alertId}&tab=comments&comments_page=1">
                        View your comment on the first page
                    </a>.</p>
                `;
                document.getElementById(`comments-list-${alertId}`).before(viewNewCommentLink);
                
                // Show success notification
                SentryNotification.success('Comment added successfully.');
            }
        } else {
            SentryNotification.error(data.errors || 'Error adding comment.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        SentryNotification.error('Error adding comment. Please try again.');
    });
}

// Function to create a comment element
function createCommentElement(comment) {
    const commentDiv = document.createElement('div');
    commentDiv.className = 'comment-item card border-0 border-start border-light-subtle ps-2 mb-1 rounded-0 hover-bg-light transition-all';
    commentDiv.setAttribute('role', 'listitem');
    commentDiv.innerHTML = `
        <div class="card-body py-0.5 px-2">
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    <span class="badge bg-light text-dark me-2 small">
                        ${comment.user}
                    </span>
                    <small class="text-muted">
                        <i class="bi bi-clock me-1" aria-hidden="true"></i>
                        Just now
                    </small>
                </div>
            </div>
            <div class="comment-content small lh-1.3">
                ${comment.text}
            </div>
        </div>
    `;
    return commentDiv;
}

// Function to get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Initialize comment forms when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners to all comment forms
    document.querySelectorAll('[id^="comment-form-"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const alertId = this.id.split('-')[2];
            submitComment(alertId);
        });
    });
}); 