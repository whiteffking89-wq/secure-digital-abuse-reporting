/**
 * Secure Digital Abuse Reporting Platform - Client-side Utilities
 */

document.addEventListener("DOMContentLoaded", () => {
    // Auto-dismiss alert notifications after 5 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    console.log("Secure Digital Abuse Reporting Platform initialized.");
});
