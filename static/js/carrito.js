// Formatea los precios con separador de miles
document.querySelectorAll('.fw-bold.text-orange.fs-5.me-2').forEach(function(span) {
    let num = span.textContent.replace(/[^0-9.]/g, '');
    if(num) {
        let partes = num.split('.');
        let miles = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        let final = (partes[1]) ? miles + '.' + partes[1] : miles;
        span.textContent = '$' + final;
    }
});

// Funcionalidad para los botones de cantidad
document.querySelectorAll('.input-group.input-group-sm.w-auto').forEach(function(group) {
    const input = group.querySelector('.input-cantidad');
    const btnPlus = group.querySelectorAll('button')[0];
    const btnMinus = group.querySelectorAll('button')[1];
    // Encuentra el stock desde el card más cercano
    const card = group.closest('.card');
    const stock = card ? parseInt(card.dataset.stock) : Infinity;

    btnPlus.addEventListener('click', function() {
        let val = parseInt(input.value) || 0;
        if (val < stock) {
            input.value = val + 1;
        }
    });

    btnMinus.addEventListener('click', function() {
        let val = parseInt(input.value) || 0;
        if (val > 0) input.value = val - 1;
    });

    input.addEventListener('input', function() {
        let val = parseInt(input.value.replace(/\D/g, '')) || 0;
        if (val > stock) val = stock;
        input.value = val;
    });
});

// Carrito global
let carrito = [];
let carritoCantidad = 0;

// Referencia al botón del carrito en el header
const btnCarrito = document.querySelector('.btn-main-orange.fw-bold');

// Crea o actualiza el badge de cantidad en el botón del carrito
function actualizarCarritoBadge() {
    let badge = btnCarrito.querySelector('.carrito-badge');
    if (!badge) {
        badge = document.createElement('span');
        badge.className = 'carrito-badge ms-2 badge bg-white text-orange fw-bold';
        btnCarrito.appendChild(badge);
    }
    badge.textContent = carritoCantidad;
    badge.style.display = carritoCantidad > 0 ? 'inline-block' : 'none';
}

// Función para agregar productos al carrito
document.querySelectorAll('.btn-add-cart').forEach(function(btn) {
    btn.addEventListener('click', function() {
        const card = btn.closest('.card');
        const input = card.querySelector('.input-cantidad');
        let cantidad = parseInt(input.value) || 0;
        if (cantidad > 0) {
            const id = card.dataset.id;
            const stock = parseInt(card.dataset.stock) || 0;
            const titulo = card.querySelector('.card-title')?.textContent.trim() || '';
            const precioTexto = card.querySelector('.fw-bold.text-orange.fs-5.me-2')?.textContent.replace(/[^0-9]/g, '') || '0';
            const precio = parseInt(precioTexto);
            const imagen = card.querySelector('img')?.getAttribute('src') || '';
            let prod = carrito.find(p => p.titulo === titulo);
            if (prod) {
                prod.cantidad += cantidad;
            } else {
                // Al agregar al carrito
                carrito.push({ id, titulo, precio, cantidad, imagen, stock });
            }
            carritoCantidad += cantidad;
            localStorage.setItem('carrito', JSON.stringify(carrito));
            actualizarCarritoBadge();
            input.value = 0;
        }
        btn.blur();
    });
});

// Mostrar el modal correcto al hacer clic en el carrito
btnCarrito.addEventListener('click', function(e) {
    e.preventDefault();
    if (carritoCantidad === 0) {
        const modal = new bootstrap.Modal(document.getElementById('modalCarrito'));
        modal.show();
    } else {
        renderizarCarrito();
        const modalLleno = new bootstrap.Modal(document.getElementById('modalCarritoLleno'));
        modalLleno.show();
    }
});

// Renderiza el contenido del carrito en el modal
function renderizarCarrito() {
    const contenedor = document.getElementById('carrito-contenido');
    const totalSpan = document.getElementById('carrito-total');
    contenedor.innerHTML = '';
    let total = 0;
    carrito.forEach(prod => {
        total += prod.precio * prod.cantidad;
        contenedor.innerHTML += `
        <div class="d-flex align-items-center justify-content-between border rounded-3 p-2 mb-3">
            <img src="${prod.imagen}" alt="${prod.titulo}" style="width:60px; height:60px; object-fit:cover;" class="me-3 rounded-2">
            <div class="flex-grow-1 text-start">
                <div class="fw-semibold">${prod.titulo}</div>
                <div class="text-orange fw-bold">$${prod.precio.toLocaleString()}</div>
            </div>
            <div class="d-flex align-items-center gap-2">
                <button class="btn btn-outline-secondary btn-sm btn-restar-prod">-</button>
                <span class="fw-bold">${prod.cantidad}</span>
                <button class="btn btn-outline-secondary btn-sm btn-sumar-prod">+</button>
                <button class="btn btn-outline-danger btn-sm btn-eliminar-prod ms-2">&times;</button>
            </div>
        </div>
        `;
    });
    totalSpan.textContent = 'Total: $' + total.toLocaleString();
}

// Funciones para los botones +, -, x dentro del modal del carrito
function agregarEventosCarritoModal() {
    // Botón sumar cantidad
    document.querySelectorAll('#carrito-contenido .btn-sumar-prod').forEach(function(btn, idx) {
        btn.onclick = function() {
            // Verifica el stock antes de sumar
            if (carrito[idx].cantidad < (carrito[idx].stock || Infinity)) {
                carrito[idx].cantidad++;
                carritoCantidad++;
                actualizarCarritoBadge();
                renderizarCarrito();
                agregarEventosCarritoModal();
            }
        };
    });
    // Botón restar cantidad
    document.querySelectorAll('#carrito-contenido .btn-restar-prod').forEach(function(btn, idx) {
        btn.onclick = function() {
            if (carrito[idx].cantidad > 1) {
                carrito[idx].cantidad--;
                carritoCantidad--;
            }
            actualizarCarritoBadge();
            renderizarCarrito();
            agregarEventosCarritoModal();
            // Si el carrito queda vacío, cerrar modal y mostrar el vacío
            if (carritoCantidad === 0) {
                const modalLleno = bootstrap.Modal.getInstance(document.getElementById('modalCarritoLleno'));
                modalLleno.hide();
                const modalVacio = new bootstrap.Modal(document.getElementById('modalCarrito'));
                modalVacio.show();
            }
        };
    });
    // Botón eliminar producto
    document.querySelectorAll('#carrito-contenido .btn-eliminar-prod').forEach(function(btn, idx) {
        btn.onclick = function() {
            carritoCantidad -= carrito[idx].cantidad;
            carrito.splice(idx, 1);
            actualizarCarritoBadge();
            renderizarCarrito();
            agregarEventosCarritoModal();
            // Si el carrito queda vacío, cerrar modal y mostrar el vacío
            if (carritoCantidad === 0) {
                const modalLleno = bootstrap.Modal.getInstance(document.getElementById('modalCarritoLleno'));
                modalLleno.hide();
                const modalVacio = new bootstrap.Modal(document.getElementById('modalCarrito'));
                modalVacio.show();
            }
        };
    });
}

// Modifica renderizarCarrito para llamar a los eventos después de renderizar
function renderizarCarrito() {
    const contenedor = document.getElementById('carrito-contenido');
    const totalSpan = document.getElementById('carrito-total');
    contenedor.innerHTML = '';
    let total = 0;
    carrito.forEach(prod => {
        total += prod.precio * prod.cantidad;
        contenedor.innerHTML += `
        <div class="d-flex align-items-center justify-content-between border rounded-3 p-2 mb-3">
            <img src="${prod.imagen}" alt="${prod.titulo}" style="width:60px; height:60px; object-fit:cover;" class="me-3 rounded-2">
            <div class="flex-grow-1 text-start">
                <div class="fw-semibold">${prod.titulo}</div>
                <div class="text-orange fw-bold">$${prod.precio.toLocaleString()}</div>
            </div>
            <div class="d-flex align-items-center gap-2">
                <button class="btn btn-outline-secondary btn-sm btn-sumar-prod">+</button>
                <span class="fw-bold">${prod.cantidad}</span>
                <button class="btn btn-outline-secondary btn-sm btn-restar-prod">-</button>
                <button class="btn btn-outline-danger btn-sm btn-eliminar-prod ms-2">&times;</button>
            </div>
        </div>
        `;
    });
    totalSpan.textContent = 'Total: $' + total.toLocaleString();
    agregarEventosCarritoModal();
}
// Inicializa el badge al cargar la página
actualizarCarritoBadge();

// // Función de filtro por categoría
// function filtrarProductos(categoria) {
//     document.querySelectorAll('#productos-row > div').forEach(function(col) {
//         let badge = col.querySelector('.badge');
//         if (!badge) return;
//         let cat = badge.textContent.trim().toLowerCase();
//         if (categoria === 'todos' || cat === categoria) {
//             col.style.display = '';
//         } else {
//             col.style.display = 'none';
//         }
//     });
// }

// // Botón "Todos los Productos"
// document.querySelector('.btn-todos-productos').addEventListener('click', function() {
//     filtrarProductos('todos');
// });

// // Botón "Navegación GPS"
// document.querySelectorAll('button').forEach(function(btn) {
//     if (btn.textContent.trim() === 'Navegación GPS') {
//         btn.addEventListener('click', function() {
//             filtrarProductos('navegacion');
//         });
//     }
// });

// // Botón "Comunicación"
// document.querySelectorAll('button').forEach(function(btn) {
//     if (btn.textContent.trim() === 'Comunicación') {
//         btn.addEventListener('click', function() {
//             filtrarProductos('comunicación');
//         });
//     }
// });

// // Botón "Iluminación"
// document.querySelectorAll('button').forEach(function(btn) {
//     if (btn.textContent.trim() === 'Iluminación') {
//         btn.addEventListener('click', function() {
//             filtrarProductos('iluminacion');
//         });
//     }
// });

// // Opciones del menú "Más categorías"
// document.querySelectorAll('.dropdown-menu .dropdown-item').forEach(function(item) {
//     item.addEventListener('click', function(e) {
//         e.preventDefault();
//         filtrarProductos(item.textContent.trim().toLowerCase());
//     });
// });

// Filtro por texto en el buscador
document.querySelector('input[placeholder="Buscar productos..."]').addEventListener('input', function() {
    const texto = this.value.trim().toLowerCase();
    document.querySelectorAll('#productos-row > div').forEach(function(col) {
        const titulo = col.querySelector('.card-title')?.textContent.toLowerCase() || '';
        const descripcion = col.querySelector('.card-text')?.textContent.toLowerCase() || '';
        if (titulo.includes(texto) || descripcion.includes(texto)) {
            col.style.display = '';
        } else {
            col.style.display = 'none';
        }
    });
});