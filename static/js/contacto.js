document.getElementById('contactForm').addEventListener('submit', function(e) {
  e.preventDefault();
  let valid = true;
  let msg = '';
  const fields = [
    { id: 'name', error: 'Ingresa un nombre válido (solo letras y espacios, mínimo 2 caracteres).' },
    { id: 'email', error: 'Ingresa un correo electrónico válido.' },
    { id: 'phone', error: 'Ingresa un número de contacto válido.' },
    { id: 'subject', error: 'El asunto debe tener al menos 3 caracteres.' },
    { id: 'message', error: 'El mensaje debe tener al menos 10 caracteres.' }
  ];

  fields.forEach(f => {
    const input = document.getElementById(f.id);
    const errorSpan = input.nextElementSibling;
    if (!input.checkValidity()) {
      errorSpan.textContent = f.error;
      valid = false;
    } else {
      errorSpan.textContent = '';
    }
  });

if (valid) {
  const data = {
    name: document.getElementById('name').value,
    email: document.getElementById('email').value,
    phone: document.getElementById('phone').value,
    subject: document.getElementById('subject').value,
    message: document.getElementById('message').value
  };

  fetch('/contacto', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  .then(res => res.ok ? res.json() : Promise.reject(res))
  .then(res => {
    document.getElementById('formMsg').textContent = '¡Registro enviado correctamente!';
    document.getElementById('contactForm').reset();
  })
  .catch(err => {
    document.getElementById('formMsg').textContent = '❌ Ocurrió un error al enviar.';
  });
}});
