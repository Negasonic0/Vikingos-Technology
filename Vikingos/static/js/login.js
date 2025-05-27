 const togglePassword = document.getElementById('togglePassword');
      const password = document.getElementById('password');
      const iconEye = document.getElementById('icon-eye');

      togglePassword.addEventListener('click', function () {
        const type = password.type === 'password' ? 'text' : 'password';
        password.type = type;
        iconEye.textContent = type === 'password' ? '👁️' : '🙈';
      });