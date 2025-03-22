document.addEventListener('DOMContentLoaded', function() {
    // Handle comment form submission
    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitButton = this.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Clear the form
                    this.reset();
                    
                    // Refresh the page to show the new comment
                    window.location.reload();
                } else {
                    // Show error message
                    alert('Error posting comment: ' + data.errors);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error posting comment. Please try again.');
            })
            .finally(() => {
                submitButton.disabled = false;
            });
        });
    }

    // Handle comment deletion
    document.querySelectorAll('.delete-comment').forEach(button => {
        button.addEventListener('click', function() {
            if (confirm('Are you sure you want to delete this comment?')) {
                const commentId = this.dataset.commentId;
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                fetch(`/alerts/comments/${commentId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Remove the comment card from the DOM
                        this.closest('.card').remove();
                        
                        // Update comment count
                        const countBadge = document.querySelector('.badge.bg-primary');
                        if (countBadge) {
                            const currentCount = parseInt(countBadge.textContent.split(' ')[0]) - 1;
                            countBadge.textContent = `${currentCount} comment${currentCount !== 1 ? 's' : ''}`;
                        }
                        
                        // Show empty state if no comments left
                        const commentsList = document.querySelector('.comments-list');
                        if (commentsList && !commentsList.querySelector('.card')) {
                            commentsList.innerHTML = `
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle"></i> No comments yet. Be the first to comment!
                                </div>
                            `;
                        }
                    } else {
                        alert('Error deleting comment: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error deleting comment. Please try again.');
                });
            }
        });
    });
}); 