// Character count functionality
function updateCharCount(textarea) {
    const maxLength = textarea.maxLength;
    const currentLength = textarea.value.length;
    document.getElementById('charCount').textContent = currentLength;
    // Also update text direction when content changes
    handleInputDirection(textarea);
}

// Helper to get the alert fingerprint from URL path or query string
function getAlertFingerprint() {
    const params = new URLSearchParams(window.location.search);
    let fp = params.get('fingerprint');
    if (!fp) {
        const parts = window.location.pathname.split('/').filter(Boolean);
        fp = parts[parts.length - 1];
    }
    return fp;
}

// Form validation
function validateCommentForm(form) {
    form.classList.add('was-validated');
    return form.checkValidity();
}

// Comment submission
function submitComment(form) {
    if (!validateCommentForm(form)) {
        return;
    }

    const commentText = form.querySelector('textarea[name="content"]').value;
    if (!commentText.trim()) {
        return;
    }

    // Show loading indicator
    document.getElementById('comment-loading').style.display = 'block';
    form.querySelector('button[type="submit"]').disabled = true;

    const formData = new FormData(form);
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
            // Reset form
            form.reset();
            form.classList.remove('was-validated');
            document.getElementById('charCount').textContent = '0';

            // Hide form container
            document.getElementById('comment-form-container').style.display = 'none';

            if (document.querySelector('#comments-list .comment-item:first-child')) {
                // We're on the first page, add the new comment
                const newComment = createCommentElement(data);
                document.querySelector('#comments-list').insertBefore(newComment, document.querySelector('#comments-list').firstChild);

                // Remove no-comments message if it exists
                const noCommentsMessage = document.getElementById('no-comments-message');
                if (noCommentsMessage) {
                    noCommentsMessage.remove();
                }
            } else {
                // If we're not on page 1, offer to navigate there
                const viewNewCommentLink = document.createElement('div');
                viewNewCommentLink.className = 'alert alert-info mt-3';
                const fingerprint = getAlertFingerprint();
                viewNewCommentLink.innerHTML = `
                    <p class="mb-0">Your comment was added successfully.
                    <a href="?fingerprint=${fingerprint}&tab=comments&comments_page=1">
                        View your comment on the first page
                    </a>.</p>
                `;
                document.querySelector('#comments-list').before(viewNewCommentLink);
            }

            // Update comment counts
            const commentCountElements = document.querySelectorAll('#comments-count, #comments-tab .badge');
            commentCountElements.forEach(element => {
                const currentCount = parseInt(element.textContent);
                if (!isNaN(currentCount)) {
                    element.textContent = (currentCount + 1).toString();
                }
            });

            SentryNotification.success('Comment added successfully.');
        } else {
            SentryNotification.error(data.errors || 'Error adding comment.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        SentryNotification.error('Error adding comment. Please try again.');
    })
    .finally(() => {
        // Hide loading indicator and re-enable submit button
        document.getElementById('comment-loading').style.display = 'none';
        form.querySelector('button[type="submit"]').disabled = false;
    });
}

// Create comment element
function createCommentElement(data) {
    const now = new Date();
    const timeString = now.toLocaleString('default', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    
    const div = document.createElement('div');
    div.className = 'list-group-item comment-item p-2 border-start-0 border-end-0 border-top-0';
    div.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-1">
            <div class="d-flex align-items-center">
                <span class="text-muted small me-2">${timeString}</span>
                <span class="fw-medium text-muted text-truncate" style="max-width: 150px;">${data.user}</span>
            </div>
            <div class="dropdown">
                <button class="btn btn-sm btn-link text-muted p-0 dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="bi bi-three-dots-vertical"></i>
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><a class="dropdown-item" href="#" data-comment-id="${data.id}" onclick="editComment(this)">
                        <i class="bi bi-pencil me-2"></i>Edit
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item text-danger" href="#" data-comment-id="${data.id}" onclick="deleteComment(this)">
                        <i class="bi bi-trash me-2"></i>Delete
                    </a></li>
                </ul>
            </div>
        </div>
        <div class="comment-content small lh-sm ps-0 text-wrap" style="white-space: pre-wrap;" data-rtl="true">${data.content}</div>
    `;

    // Apply RTL detection to the new comment content
    const commentContent = div.querySelector('.comment-content');
    setTextDirection(commentContent);
    
    return div;
}

// Edit comment functionality
function editComment(element) {
    const commentId = element.dataset.commentId;
    const commentItem = element.closest('.comment-item');
    const commentContent = commentItem.querySelector('.comment-content');
    const originalContent = commentContent.textContent;

    // Create edit form
    const editForm = document.createElement('form');
    editForm.className = 'edit-comment-form mb-2';
    editForm.innerHTML = `
        <div class="mb-2 position-relative">
            <textarea class="form-control form-control-sm" rows="2" required maxlength="1000" data-rtl="true">${originalContent}</textarea>
            <small class="text-muted position-absolute end-0 bottom-0 pe-2 mb-1">
                <span class="edit-char-count">${originalContent.length}</span>/1000
            </small>
        </div>
        <div class="d-flex justify-content-end gap-2">
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="cancelEdit(this)">Cancel</button>
            <button type="submit" class="btn btn-sm btn-primary">Save</button>
        </div>
    `;

    // Hide original content and show edit form
    commentContent.style.display = 'none';
    commentContent.after(editForm);

    // Add character count listener and set initial text direction
    const textarea = editForm.querySelector('textarea');
    handleInputDirection(textarea);
    textarea.addEventListener('input', () => {
        editForm.querySelector('.edit-char-count').textContent = textarea.value.length;
        handleInputDirection(textarea);
    });

    // Handle form submission
    editForm.addEventListener('submit', function(e) {
        e.preventDefault();
        // TODO: Implement edit submission
        SentryNotification.info('Edit functionality coming soon');
        cancelEdit(this.querySelector('button[type="button"]'));
    });
}

// Cancel edit
function cancelEdit(button) {
    const editForm = button.closest('.edit-comment-form');
    const commentContent = editForm.previousElementSibling;
    commentContent.style.display = '';
    editForm.remove();
}

// Delete comment functionality
function deleteComment(element) {
    const commentId = element.dataset.commentId;
    if (confirm('Are you sure you want to delete this comment?')) {
        // TODO: Implement delete functionality
        SentryNotification.info('Delete functionality coming soon');
    }
}

// Initialize comment functionality
document.addEventListener('DOMContentLoaded', function() {
    // Toggle comment form
    const addCommentToggle = document.getElementById('add-comment-toggle');
    const commentFormContainer = document.getElementById('comment-form-container');
    const cancelCommentButton = document.getElementById('cancel-comment');
    const commentForm = document.getElementById('commentForm');
    const commentTextarea = document.getElementById('commentText');

    if (addCommentToggle) {
        addCommentToggle.addEventListener('click', function() {
            commentFormContainer.style.display = 'block';
            commentTextarea.focus();
        });
    }

    if (cancelCommentButton) {
        cancelCommentButton.addEventListener('click', function() {
            commentFormContainer.style.display = 'none';
            commentForm.reset();
            commentForm.classList.remove('was-validated');
            document.getElementById('charCount').textContent = '0';
        });
    }

    if (commentTextarea) {
        // Set initial direction
        handleInputDirection(commentTextarea);
        
        commentTextarea.addEventListener('input', function() {
            updateCharCount(this);
        });
    }

    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitComment(this);
        });
    }

    // Apply RTL detection to existing comments
    document.querySelectorAll('.comment-content').forEach(setTextDirection);
}); 