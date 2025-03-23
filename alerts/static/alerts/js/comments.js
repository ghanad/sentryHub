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
            
            // Add the new comment to the comments list
            const commentsList = document.getElementById(`comments-list-${alertId}`);
            const newComment = createCommentElement(data.comment);
            commentsList.insertBefore(newComment, commentsList.firstChild);
            
            // Show success notification
            SentryNotification.success('Comment added successfully.');
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
    commentDiv.className = 'comment mb-3';
    commentDiv.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div>
                <strong>${comment.user}</strong>
                <small class="text-muted ms-2">${comment.created_at}</small>
            </div>
        </div>
        <p class="mb-0">${comment.text}</p>
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