document.addEventListener('DOMContentLoaded', () => {
    const syncBtn = document.getElementById('syncBtn');
    const syncSpinner = document.getElementById('syncSpinner');
    const syncText = document.getElementById('syncText');

    if (syncBtn) {
        syncBtn.addEventListener('click', async () => {
            // UI Loading State
            syncBtn.disabled = true;
            syncSpinner.style.display = 'inline-block';
            syncText.textContent = 'Syncing...';

            try {
                // Call the Producer View without IP params (uses backend default)
                const response = await fetch('/sync-logs/');
                const data = await response.json();

                if (response.ok) {
                    showToast("✓ Sync started! Processing attendance data...");

                    // Update sync text to show processing
                    syncText.textContent = 'Processing...';

                    // Wait longer for Kafka consumer to process (5 seconds)
                    // Then reload to show updated data
                    setTimeout(() => {
                        showToast("✓ Sync complete! Refreshing...");
                        setTimeout(() => location.reload(), 1000);
                    }, 5000);
                } else {
                    showToast("✗ Error: " + data.message, true);
                    // Reset UI on error
                    syncBtn.disabled = false;
                    syncSpinner.style.display = 'none';
                    syncText.textContent = 'Sync Now';
                }
            } catch (error) {
                showToast("✗ Network Error: " + error, true);
                // Reset UI on error
                syncBtn.disabled = false;
                syncSpinner.style.display = 'none';
                syncText.textContent = 'Sync Now';
            }
        });
    }

    function showToast(msg, isError = false) {
        // Build toast dynamically if not exists, or verify standard toast present
        let toast = document.getElementById('toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toast';
            toast.style.position = 'fixed';
            toast.style.bottom = '2rem';
            toast.style.right = '2rem';
            toast.style.padding = '1rem 2rem';
            toast.style.borderRadius = '12px';
            toast.style.background = '#10b981';
            toast.style.color = 'white';
            toast.style.transition = 'all 0.3s ease';
            toast.style.transform = 'translateY(150%)';
            toast.style.boxShadow = '0 10px 30px -10px rgba(0,0,0,0.5)';
            toast.style.zIndex = '9999';
            document.body.appendChild(toast);
        }

        toast.textContent = msg;
        toast.style.background = isError ? '#ef4444' : '#10b981';
        toast.style.transform = 'translateY(0)';

        setTimeout(() => {
            toast.style.transform = 'translateY(150%)';
        }, 3000);
    }
});
