const modal = document.getElementById('modal');
const backdrop = document.getElementById('backdrop');
const openBtn = document.getElementById('openModal');
const closeBtn = document.getElementById('closeModal');

function openModal() {
    modal.classList.remove('modal-hidden');
    modal.classList.add('modal-visible');
    backdrop.classList.remove('opacity-0', 'pointer-events-none');
    backdrop.classList.add('opacity-100');
}

function closeModal() {
    modal.classList.remove('modal-visible');
    modal.classList.add('modal-hidden');
    backdrop.classList.remove('opacity-100');
    backdrop.classList.add('opacity-0', 'pointer-events-none');
}

openBtn.addEventListener('click', openModal);
closeBtn.addEventListener('click', closeModal);
backdrop.addEventListener('click', closeModal);

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('modal-hidden')) {
        closeModal();
    }
});
