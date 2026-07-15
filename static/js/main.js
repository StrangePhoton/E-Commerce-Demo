document.addEventListener('DOMContentLoaded', function() {
    const categoriesButton = document.getElementById('categoriesButton');
    const categoriesMenu = document.getElementById('categoriesMenu');
    
    // If the page does not have the button or menu (some pages may be hidden), return an error to avoid:
    if (!categoriesButton || !categoriesMenu) return;

    // Create the overlay (darkening) or select if it exists
    let overlay = document.querySelector('.menu-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'menu-overlay';
        document.body.appendChild(overlay);
    }

    function toggleMenu() {
        const isOpen = categoriesMenu.classList.toggle('show');
        overlay.classList.toggle('show');
        categoriesButton.setAttribute('aria-expanded', isOpen);
    }

    function closeMenu() {
        categoriesMenu.classList.remove('show');
        overlay.classList.remove('show');
        categoriesButton.setAttribute('aria-expanded', 'false');
    }

    // Button click
    categoriesButton.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        toggleMenu();
    });

    // Click outside or overlay
    document.addEventListener('click', function(e) {
        if (!categoriesMenu.contains(e.target) && !categoriesButton.contains(e.target)) {
            closeMenu();
        }
    });

    // ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeMenu();
    });
});