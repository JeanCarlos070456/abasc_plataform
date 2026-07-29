(() => {
    const toggle = document.querySelector('[data-menu-toggle]');
    const menu = document.querySelector('[data-main-menu]');

    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            const open = menu.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', String(open));
            toggle.textContent = open ? '✕' : '☰';
        });
    }

    document.querySelectorAll('.alert').forEach((alert) => {
        window.setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-8px)';
            window.setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
})();
