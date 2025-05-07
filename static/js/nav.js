const menuToggle = document.getElementById('menu-toggle');
const sidebar = document.getElementById('sidebar');

menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('-translate-x-full');
});

document.addEventListener('click', (e) => {
    if (!sidebar.contains(e.target) && !menuToggle.contains(e.target) && window.innerWidth < 768) {
        sidebar.classList.add('-translate-x-full');
    }
});

// Submenu toggle functionality
const submenuToggles = document.querySelectorAll('.submenu-toggle');
submenuToggles.forEach(toggle => {
    toggle.addEventListener('click', () => {
        const submenu = toggle.nextElementSibling;
        const arrow = toggle.querySelector('svg:last-child');
        submenu.classList.toggle('open');
        arrow.classList.toggle('rotate-180');
    });
});

// Active menu item highlighting
const menuItems = document.querySelectorAll('.menu-item');
const currentPage = window.location.pathname.split('/').pop().replace('.html', '');

menuItems.forEach(item => {
    const page = item.getAttribute('data-page');
    if (page === currentPage) {
        item.classList.add('active');
        item.querySelector('svg').classList.add('text-blue-500');
        item.querySelector('span').classList.add('text-blue-600');
    }
});