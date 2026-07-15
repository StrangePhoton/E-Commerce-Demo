// Your JavaScript code here
console.log('Script loaded successfully!');

document.addEventListener('DOMContentLoaded', function() {
    const categoriesButton = document.getElementById('categoriesButton');
    const categoriesMenu = document.getElementById('categoriesMenu');
    
    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = 'menu-overlay';
    document.body.appendChild(overlay);

    // Toggle menu function
    function toggleMenu() {
        categoriesMenu.classList.toggle('show');
        overlay.classList.toggle('show');
        
        // Toggle aria-expanded for accessibility
        const isExpanded = categoriesMenu.classList.contains('show');
        categoriesButton.setAttribute('aria-expanded', isExpanded);
    }

    // Event Listeners
    categoriesButton.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleMenu();
    });

    // Close menu when clicking overlay
    overlay.addEventListener('click', toggleMenu);

    // Close menu when pressing ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && categoriesMenu.classList.contains('show')) {
            toggleMenu();
        }
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!categoriesMenu.contains(e.target) && 
            !categoriesButton.contains(e.target) && 
            categoriesMenu.classList.contains('show')) {
            toggleMenu();
        }
    });
}); 