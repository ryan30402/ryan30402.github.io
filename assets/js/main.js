(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('[data-theme-toggle]');
  const isLight = () => root.dataset.theme === 'light';

  function setTheme(theme) {
    if (theme === 'light') root.dataset.theme = 'light';
    else root.removeAttribute('data-theme');
    try { localStorage.setItem('ryan-portfolio-theme', theme); } catch (_) {}
    if (themeButton) {
      themeButton.setAttribute('aria-label', `Switch to ${theme === 'light' ? 'dark' : 'light'} theme`);
      themeButton.setAttribute('title', `Switch to ${theme === 'light' ? 'dark' : 'light'} theme`);
      const sun = themeButton.querySelector('[data-icon="sun"]');
      const moon = themeButton.querySelector('[data-icon="moon"]');
      if (sun) sun.hidden = theme === 'light';
      if (moon) moon.hidden = theme !== 'light';
    }
  }
  setTheme(isLight() ? 'light' : 'dark');
  themeButton?.addEventListener('click', () => setTheme(isLight() ? 'dark' : 'light'));

  const menuButton = document.querySelector('[data-menu-toggle]');
  const nav = document.querySelector('[data-primary-nav]');
  function closeMenu() {
    menuButton?.setAttribute('aria-expanded', 'false');
    nav?.classList.remove('is-open');
  }
  menuButton?.addEventListener('click', () => {
    const expanded = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!expanded));
    nav?.classList.toggle('is-open', !expanded);
  });
  nav?.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  window.addEventListener('resize', () => { if (window.innerWidth > 800) closeMenu(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeMenu(); });
  document.addEventListener('click', event => {
    if (nav?.classList.contains('is-open') && !nav.contains(event.target) && !menuButton?.contains(event.target)) closeMenu();
  });

  const chips = [...document.querySelectorAll('[data-filter]')];
  const cards = [...document.querySelectorAll('[data-category]')];
  chips.forEach(chip => chip.addEventListener('click', () => {
    const filter = chip.dataset.filter;
    chips.forEach(other => other.setAttribute('aria-pressed', String(other === chip)));
    cards.forEach(card => { card.hidden = filter !== 'all' && card.dataset.category !== filter; });
    const count = document.querySelector('[data-filter-count]');
    if (count) count.textContent = String(cards.filter(card => !card.hidden).length);
  }));
})();
