// This script adds the diarization toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    // Toggle diarization options visibility
    const diarizeCheckbox = document.getElementById('option-diarize');
    if (diarizeCheckbox) {
        diarizeCheckbox.addEventListener('change', function() {
            const diarizeOptions = document.querySelectorAll('.diarize-options');
            diarizeOptions.forEach(option => {
                option.style.display = this.checked ? 'flex' : 'none';
            });
        });
    }
});
