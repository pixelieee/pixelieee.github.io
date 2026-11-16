const search = document.querySelector('#search');
if (search) {
  const cards = [...document.querySelectorAll('[data-search]')];
  const empty = document.querySelector('#empty');
  const count = document.querySelector('#result-count');
  search.addEventListener('input', () => {
    const q = search.value.trim().toLocaleLowerCase();
    let matches = 0;
    for (const card of cards) {
      const visible = card.dataset.search.toLocaleLowerCase().includes(q);
      card.hidden = !visible;
      matches += Number(visible);
    }
    empty.hidden = matches !== 0;
    count.textContent = `${matches} 篇`;
  });
  search.addEventListener('keydown', e => {
    if (e.key === 'Escape') { search.value = ''; search.dispatchEvent(new Event('input')); }
  });
}
