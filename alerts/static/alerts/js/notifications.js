// SentryNotification object for handling notifications
const SentryNotification = {
    success: function(message) {
        toastr.success(message);
    },
    error: function(message) {
        toastr.error(message);
    },
    warning: function(message) {
        toastr.warning(message);
    },
    info: function(message) {
        toastr.info(message);
    }
}; 