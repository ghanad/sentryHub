// Function to handle comment submission
function submitComment(form) {
    const commentText = form.querySelector('textarea[name="content"]').value;
    
    if (!commentText.trim()) {
        SentryNotification.warning('Please enter a comment before submitting.');
        return;
    }

    // Get CSRF token from cookie
    const csrftoken = getCookie('csrftoken');

    // Get the alert fingerprint from the URL
    const urlParams = new URLSearchParams(window.location.search);
    const fingerprint = urlParams.get('fingerprint');

    // Send the comment to the server
    fetch(window.location.href, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: new URLSearchParams({
            'content': commentText,
            'comment': '1',
            'csrfmiddlewaretoken': csrftoken
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Clear the comment input
            form.querySelector('textarea[name="content"]').value = '';
            
            // Check if we're on the first page before attempting to add the comment to the UI
            const currentPage = parseInt(urlParams.get('comments_page') || '1');
            
            if (currentPage === 1) {
                // Add the new comment to the list
                const commentsList = document.getElementById('comments-list');
                const newComment = createCommentElement({
                    user: data.user,
                    text: data.content
                });
                commentsList.insertBefore(newComment, commentsList.firstChild);
                
                // Remove the "no comments" message if it exists
                const noCommentsMessage = document.getElementById('no-comments-message');
                if (noCommentsMessage) {
                    noCommentsMessage.remove();
                }
                
                // Update comment count in both the tab badge and the comments header
                const commentCountElements = document.querySelectorAll('#comments-count, #comments-tab .badge');
                commentCountElements.forEach(element => {
                    const currentCount = parseInt(element.textContent);
                    if (!isNaN(currentCount)) {
                        element.textContent = (currentCount + 1).toString();
                    }
                });
                
                // Show success notification
                SentryNotification.success('Comment added successfully.');
            } else {
                // If we're not on page 1, offer to navigate there to see the new comment
                const viewNewCommentLink = document.createElement('div');
                viewNewCommentLink.className = 'alert alert-info mt-3';
                viewNewCommentLink.innerHTML = `
                    <p class="mb-0">Your comment was added successfully. 
                    <a href="?fingerprint=${fingerprint}&tab=comments&comments_page=1">
                        View your comment on the first page
                    </a>.</p>
                `;
                document.getElementById('comments-list').before(viewNewCommentLink);
                
                // Update comment count in both the tab badge and the comments header
                const commentCountElements = document.querySelectorAll('#comments-count, #comments-tab .badge');
                commentCountElements.forEach(element => {
                    const currentCount = parseInt(element.textContent);
                    if (!isNaN(currentCount)) {
                        element.textContent = (currentCount + 1).toString();
                    }
                });
                
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
    // Function to detect Persian text
    function isPersianText(text) {
        // Persian Unicode range: \u0600-\u06FF
        const persianRegex = /[\u0600-\u06FF]/;
        return persianRegex.test(text);
    }

    // Function to set text direction based on content
    function setTextDirection(element) {
        if (isPersianText(element.textContent)) {
            element.style.direction = 'rtl';
            element.style.textAlign = 'right';
        } else {
            element.style.direction = 'ltr';
            element.style.textAlign = 'left';
        }
    }

    // Function to handle input direction
    function handleInputDirection(event) {
        const textarea = event.target;
        if (isPersianText(textarea.value)) {
            textarea.style.direction = 'rtl';
            textarea.style.textAlign = 'right';
        } else {
            textarea.style.direction = 'ltr';
            textarea.style.textAlign = 'left';
        }
    }

    // Apply RTL detection to existing comments
    document.querySelectorAll('.comment-content').forEach(setTextDirection);

    // Add input event listener to comment textarea
    const commentTextarea = document.querySelector('#commentText');
    if (commentTextarea) {
        commentTextarea.addEventListener('input', handleInputDirection);
        // Set initial direction
        handleInputDirection({ target: commentTextarea });
    }

    // Toggle comment form visibility
    const addCommentBtn = document.getElementById('add-comment-toggle');
    const cancelCommentBtn = document.getElementById('cancel-comment');
    const commentFormContainer = document.getElementById('comment-form-container');

    if (addCommentBtn && commentFormContainer) {
        addCommentBtn.addEventListener('click', function() {
            commentFormContainer.style.display = 'block';
            addCommentBtn.style.display = 'none';
            commentTextarea.focus();
        });
    }

    if (cancelCommentBtn && commentFormContainer && addCommentBtn) {
        cancelCommentBtn.addEventListener('click', function() {
            commentFormContainer.style.display = 'none';
            addCommentBtn.style.display = 'block';
            commentTextarea.value = '';
        });
    }

    // Handle comment form submission
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation(); // Prevent other handlers from catching this event
            
            const submitButton = this.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            
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
                    // Show success message with new notification system
                    SentryNotification.success("Comment added successfully.");
                    
                    // Clear the form
                    this.reset();
                    
                    // Hide the form and show the add button again
                    commentFormContainer.style.display = 'none';
                    addCommentBtn.style.display = 'block';
                    
                    // Check if we're on the first page before attempting to add the comment to the UI
                    const urlParams = new URLSearchParams(window.location.search);
                    const currentPage = parseInt(urlParams.get('comments_page') || '1');
                    
                    if (currentPage === 1) {
                        // Add the new comment to the list
                        const commentsContainer = document.getElementById('comments-list');
                        
                        // Remove the "no comments" message if it exists
                        const noCommentsMessage = document.getElementById('no-comments-message');
                        if (noCommentsMessage) {
                            noCommentsMessage.remove();
                        }
                        
                        // Create a new comment element
                        const newComment = document.createElement('div');
                        newComment.className = 'list-group-item comment-item p-2 border-start-0 border-end-0';
                        
                        // Add border-bottom-0 class to the previous first item if it exists
                        const firstItem = commentsContainer.querySelector('.comment-item');
                        if (firstItem) {
                            firstItem.classList.remove('border-bottom-0');
                        }
                        
                        newComment.innerHTML = `
                            <div class="d-flex align-items-baseline mb-1">
                                <span class="fw-medium me-2 text-truncate" style="max-width: 150px;">${data.user}</span>
                                <small class="text-muted ms-auto flex-shrink-0">Just now</small>
                            </div>
                            <div class="comment-content small lh-sm ps-0 text-wrap" style="white-space: pre-wrap;">${data.content}</div>
                        `;
                        
                        // Insert at the beginning of the comments list
                        if (commentsContainer.firstChild) {
                            commentsContainer.insertBefore(newComment, commentsContainer.firstChild);
                        } else {
                            commentsContainer.appendChild(newComment);
                        }
                        
                        // Apply RTL detection to the new comment
                        const newCommentText = newComment.querySelector('.comment-content');
                        setTextDirection(newCommentText);
                        
                        // Update pagination if needed
                        const paginationNav = document.querySelector('#comments nav');
                        if (!paginationNav && document.querySelectorAll('#comments-list .comment-item').length > 10) {
                            // We've just crossed the threshold for pagination, reload the page to show pagination
                            window.location.reload();
                        }
                    } else {
                        // If we're not on page 1, offer to navigate there to see the new comment
                        const viewNewCommentLink = document.createElement('div');
                        viewNewCommentLink.className = 'alert alert-info mt-3';
                        viewNewCommentLink.innerHTML = `
                            <p class="mb-0">Your comment was added successfully. 
                            <a href="?fingerprint=${window.location.href.split('fingerprint=')[1].split('&')[0]}&tab=comments&comments_page=1">
                                View your comment on the first page
                            </a>.</p>
                        `;
                        document.querySelector('#comments-list').before(viewNewCommentLink);
                    }
                    
                    // Update the total comment count (in header and badge)
                    const commentCountEl = document.getElementById('comments-count');
                    if (commentCountEl) {
                        const currentCount = parseInt(commentCountEl.textContent);
                        if (!isNaN(currentCount)) {
                            commentCountEl.textContent = (currentCount + 1).toString();
                        }
                    }
                    
                    const tabBadge = document.querySelector('#comments-tab .badge');
                    if (tabBadge) {
                        const badgeCount = parseInt(tabBadge.textContent);
                        if (!isNaN(badgeCount)) {
                            tabBadge.textContent = (badgeCount + 1).toString();
                        }
                    }
                } else {
                    SentryNotification.error(data.errors || "Error adding comment.");
                }
            })
            .catch(error => {
                console.error('Error:', error);
                SentryNotification.error("Error adding comment. Please try again.");
            })
            .finally(() => {
                submitButton.disabled = false;
            });
        });
    }
}); 