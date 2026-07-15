function getBasePath() {
    const path = window.location.pathname;
    const depth = (path.match(/\//g) || []).length;
    return '../'.repeat(depth - 1);
}

document.addEventListener('DOMContentLoaded', function() {
    const categoriesButton = document.getElementById('categoriesButton');
    const categoriesMenu = document.getElementById('categoriesMenu');
    
    // Toggle menu when button is clicked
    categoriesButton.addEventListener('click', function(e) {
        e.stopPropagation();
        categoriesMenu.classList.toggle('show');
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!categoriesMenu.contains(e.target) && !categoriesButton.contains(e.target)) {
            categoriesMenu.classList.remove('show');
        }
    });

    // Close menu when pressing ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && categoriesMenu.classList.contains('show')) {
            categoriesMenu.classList.remove('show');
        }
    });
});

function initializeHeader() {
    const categoriesButton = document.getElementById('categoriesButton');
    const categoriesMenu = document.getElementById('categoriesMenu');
    
    if (categoriesButton && categoriesMenu) {
        categoriesButton.addEventListener('click', function() {
            categoriesMenu.classList.toggle('show');
        });
    }
} 