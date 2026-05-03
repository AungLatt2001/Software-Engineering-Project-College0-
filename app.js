const navBtns = document.querySelectorAll('.nav-btn');
const cards = document.querySelectorAll('.card');
const modal = document.getElementById('modal');
const modalImg = document.getElementById('modalImg');
const modalTitle = document.getElementById('modalTitle');
const modalClose = document.getElementById('modalClose');

navBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    navBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const target = btn.dataset.target;
    cards.forEach(card => {
      if (target === 'all' || card.dataset.name === target) {
        card.classList.remove('hidden');
      } else {
        card.classList.add('hidden');
      }
    });
  });
});

cards.forEach(card => {
  card.addEventListener('click', () => {
    const img = card.querySelector('img');
    const label = card.querySelector('.card-label').textContent;
    modalImg.src = img.src;
    modalImg.alt = img.alt;
    modalTitle.textContent = label;
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  });
});

modalClose.addEventListener('click', closeModal);
modal.addEventListener('click', e => {
  if (e.target === modal) closeModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

function closeModal() {
  modal.classList.remove('open');
  document.body.style.overflow = '';
}
