function openLoginModal() {
  document.getElementById('loginModal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeLoginModal() {
  document.getElementById('loginModal').classList.remove('open');
  document.body.style.overflow = '';
}

document.addEventListener('DOMContentLoaded', function () {
  var modal = document.getElementById('loginModal');
  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal) closeLoginModal();
    });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeLoginModal();
  });
});
