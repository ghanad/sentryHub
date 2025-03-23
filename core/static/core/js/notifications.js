/**
 * SentryNotification: سیستم یکپارچه نوتیفیکیشن برای SentryHub
 */
const SentryNotification = {
    // نمایش نوتیفیکیشن موفقیت
    success: function(message, options = {}) {
        this._showNotification('success', message, options);
    },

    // نمایش نوتیفیکیشن خطا
    error: function(message, options = {}) {
        this._showNotification('error', message, options);
    },

    // نمایش نوتیفیکیشن هشدار
    warning: function(message, options = {}) {
        this._showNotification('warning', message, options);
    },

    // نمایش نوتیفیکیشن اطلاعات
    info: function(message, options = {}) {
        this._showNotification('info', message, options);
    },

    // پاک کردن همه نوتیفیکیشن‌ها
    clearAll: function() {
        if (typeof toastr !== 'undefined') {
            toastr.clear();
        }
    },

    // تابع داخلی برای نمایش نوتیفیکیشن
    _showNotification: function(type, message, options) {
        // پاک کردن نوتیفیکیشن‌های قبلی اگر گزینه مربوطه فعال باشد
        if (options.clearBeforeShow !== false) {
            this.clearAll();
        }

        // تنظیمات پیش‌فرض
        const defaultOptions = {
            closeButton: true,
            progressBar: true,
            positionClass: "toast-top-right",
            timeOut: 5000,
            extendedTimeOut: 1000,
            preventDuplicates: true,
            newestOnTop: true,
            showEasing: "swing",
            hideEasing: "linear",
            showMethod: "fadeIn",
            hideMethod: "fadeOut"
        };
        
        // ترکیب تنظیمات پیش‌فرض با تنظیمات ارسالی
        const settings = {...defaultOptions, ...options};
        
        // اطمینان از وجود toastr
        if (typeof toastr !== 'undefined') {
            // کانفیگ کردن toastr
            toastr.options = settings;
            
            // نمایش نوتیفیکیشن
            toastr[type](message);
        } else {
            console.error('Toastr library is not available!');
        }
    }
};

// تنظیم خودکار toastr (اگر موجود باشد)
document.addEventListener('DOMContentLoaded', function() {
    if (typeof toastr !== 'undefined') {
        toastr.options = {
            closeButton: true,
            progressBar: true,
            positionClass: "toast-top-right",
            timeOut: 5000
        };
    }
}); 