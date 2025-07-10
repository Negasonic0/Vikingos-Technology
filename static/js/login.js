const togglePassword = document.getElementById('toggle-password');
const password = document.getElementById('password-input');

togglePassword.addEventListener('click', function () {
  const type = password.type === 'password' ? 'text' : 'password';
  password.type = type;
  // Cambia el icono si quieres:
  togglePassword.textContent = type === 'password' ? '👁️' : '🙈';
});