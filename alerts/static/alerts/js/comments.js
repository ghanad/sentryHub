// File: /static/alerts/js/revised-comments.js
document.addEventListener('DOMContentLoaded', function() {
    // Clear any existing toastr notifications first
    if (typeof toastr !== 'undefined') {
        toastr.clear();
    }

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
                    // Clear all existing toasts first
                    toastr.clear();
                    
                    // Then show success message
                    toastr.success("Comment added successfully.");
                    
                    // Clear the form
                    this.reset();
                    
                    // Add the new comment to the list
                    const commentsContainer = document.getElementById('comments-list');
                    
                    // Remove the "no comments" message if it exists
                    const noCommentsMessage = document.getElementById('no-comments-message');
                    if (noCommentsMessage) {
                        noCommentsMessage.remove();
                    }
                    
                    // Create a new comment element
                    const newComment = document.createElement('div');
                    newComment.className = 'comment-item card border-0 border-start border-light-subtle ps-2 mb-1 rounded-0 hover-bg-light transition-all';
                    newComment.setAttribute('role', 'listitem');
                    newComment.innerHTML = `
                        <div class="card-body py-0.5 px-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="d-flex align-items-center">
                                    <span class="badge bg-light text-dark me-2 small">
                                        ${data.user}
                                    </span>
                                    <small class="text-muted">
                                        <i class="bi bi-clock me-1" aria-hidden="true"></i>
                                        Just now
                                    </small>
                                </div>
                            </div>
                            <div class="comment-content small lh-1.3">
                                ${data.content}
                            </div>
                        </div>
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
                    
                    // Update the comment count
                    const commentCount = document.getElementById('comments-count');
                    if (commentCount) {
                        const currentCount = parseInt(commentCount.textContent);
                        commentCount.textContent = (currentCount + 1).toString();
                    }
                } else {
                    // Clear all existing toasts first
                    toastr.clear();
                    
                    toastr.error(data.errors || "Error adding comment.");
                }
            })
            .catch(error => {
                console.error('Error:', error);
                toastr.error("Error adding comment. Please try again.");
            })
            .finally(() => {
                submitButton.disabled = false;
            });
        });
    }
});