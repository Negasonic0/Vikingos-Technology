// Función para formatear moneda en JavaScript (para uso en el modal, si es necesario)
function formatCurrencyJs(value) {
    try {
        let num_value = parseFloat(String(value).replace(/\./g, '').replace(/,/g, '.'));
        if (isNaN(num_value)) return value;

        num_value = Math.round(num_value * 100) / 100;

        if (num_value === parseInt(num_value)) {
            return `$${num_value.toLocaleString('es-CO')}`;
        } else {
            return `$${num_value.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }
    } catch (e) {
        console.error("Error al formatear moneda:", e);
        return value;
    }
}

// Función para mostrar los productos en el carrito y calcular el subtotal/total
function mostrarCarrito() {
    const contenedor = document.getElementById('productos-carrito');
    const carrito = JSON.parse(localStorage.getItem('carrito')) || [];
    console.log('Carrito:', carrito);
    let subtotal = 0;
    contenedor.innerHTML = '';


    carrito.forEach(producto => {
        const totalProducto = producto.precio * producto.cantidad;
        subtotal += totalProducto;

        contenedor.innerHTML += `
        <div class="card mb-3 border-0" data-id="${producto.id}" data-stock="${producto.stock}">
            <div class="card-body d-flex align-items-center">
                <img src="${producto.imagen}" alt="Producto" width="70" height="70" class="rounded me-3" style="object-fit:cover;">
                <div class="flex-grow-1">
                    <div class="fw-bold">${producto.titulo}</div>
                    <div class="text-white fw-bold">${formatCurrencyJs(producto.precio)}</div>
                </div>
                <div class="d-flex align-items-center ms-3">
                    <button class="btn btn-outline-secondary btn-sm fw-bold" onclick="cambiarCantidad('${producto.id}', -1)">-</button>
                    <span class="mx-2 fs-5">${producto.cantidad}</span>
                    <button class="btn btn-outline-secondary btn-sm fw-bold" onclick="cambiarCantidad('${producto.id}', 1)">+</button>
                </div>
                <div class="ms-4 fw-bold fs-5">${formatCurrencyJs(totalProducto)}</div>
                <button class="btn btn-link text-danger ms-3 fs-4" title="Eliminar" onclick="eliminarProducto('${producto.id}')">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        </div>
        `;
    });

    const descuentoInput = document.getElementById('descuento');
    let porcentajeDescuento = parseFloat(descuentoInput.value) || 0;
    // Limitar el descuento entre 0 y 100
    if (porcentajeDescuento < 0) {
        porcentajeDescuento = 0;
        descuentoInput.value = 0;
    } else if (porcentajeDescuento > 100) {
        porcentajeDescuento = 100;
        descuentoInput.value = 100;
    }
    // Redondear el descuento a máximo 2 decimales
    porcentajeDescuento = Math.round(porcentajeDescuento * 100) / 100;
    const montoDescuento = Math.round((subtotal * (porcentajeDescuento / 100)) * 100) / 100;
    const totalConDescuento = Math.round((subtotal - montoDescuento) * 100) / 100;

    document.getElementById('subtotal-carrito').textContent = formatCurrencyJs(subtotal);
    document.getElementById('total-carrito').textContent = formatCurrencyJs(totalConDescuento);

    let descuentoHtml = document.getElementById('descuento-carrito');
    if (!descuentoHtml) {
        descuentoHtml = document.createElement('div');
        descuentoHtml.id = 'descuento-carrito';
        descuentoHtml.className = 'd-flex justify-content-between mb-2';
        document.getElementById('subtotal-carrito').parentNode.after(descuentoHtml);
    }
    descuentoHtml.innerHTML = `
        <span class="resumen-label">Descuento (${porcentajeDescuento}%):</span>
        <span class="fw-bold text-white">-${formatCurrencyJs(montoDescuento)}</span>
    `;
}

function mostrarToastFacturaExitosa() {
  const toastEl = document.getElementById('toastFacturaExitosa');
  const toast = new bootstrap.Toast(toastEl, {
    delay: 10000, // 4 segundos
    autohide: true
  });
  toast.show();
}

// Event listener para el campo de descuento
document.getElementById('descuento').addEventListener('input', mostrarCarrito);

function vaciarCarrito() {
    localStorage.removeItem('carrito');
    mostrarCarrito();
}

// ✅ Función que envía el formulario y habilita el botón "Enviar Factura"
function enviarFormulario() {
    const carrito = JSON.parse(localStorage.getItem('carrito')) || [];
    if (carrito.length === 0) {
        mostrarMensajeModal('El carrito está vacío.', 'danger');
        return;
    }

    document.getElementById("productosInput").value = JSON.stringify(carrito);

    // Mostrar mensaje de éxito
    // mostrarToastFacturaExitosa();

    // Enviar formulario después de un pequeño retardo (opcional)
    setTimeout(() => {
        console.log("Enviando formulario...");
        document.getElementById("formVenta").submit();
    }, 500);
}

function cambiarCantidad(id, cambio) {
    let carrito = JSON.parse(localStorage.getItem('carrito')) || [];
    // Busca el card correspondiente al producto usando el id
    const card = document.querySelector(`.card[data-id="${id}"]`);
    const stock = card ? parseInt(card.dataset.stock) : Infinity;
    carrito = carrito.map(producto => {
        if (producto.id === id) {
            // Asegurarse de que el cambio no exceda el stock
            if ((producto.cantidad + cambio) <= stock) 
                producto.cantidad += cambio;
                // Asegurarse de que la cantidad no sea menor a 1 y no exceda el stock
                if (producto.cantidad < 1) producto.cantidad = 1;
        }
        return producto;
    });
    localStorage.setItem('carrito', JSON.stringify(carrito));
    mostrarCarrito();
}

function eliminarProducto(id) {
    let carrito = JSON.parse(localStorage.getItem('carrito')) || [];
    carrito = carrito.filter(producto => producto.id !== id);
    localStorage.setItem('carrito', JSON.stringify(carrito));
    mostrarCarrito();
}

function agregarAlCarrito(producto) {
    let carrito = JSON.parse(localStorage.getItem('carrito')) || [];
    let existente = carrito.find(p => p.id === producto.id);

    if (existente) {
        existente.cantidad += 1;
    } else {
        producto.cantidad = 1;
        carrito.push(producto);
    }
    localStorage.setItem('carrito', JSON.stringify(carrito));
    mostrarNotificacion();
}

function mostrarNotificacion() {
    const noti = document.getElementById('notificacion');
    noti.style.display = 'block';
    setTimeout(() => {
        noti.style.display = 'none';
    }, 2000);
}

document.getElementById('formVenta').addEventListener('submit', function(e) {
    const descuento = parseFloat(document.getElementById('descuento').value);
    if (descuento < 0 || descuento > 100) {
        mostrarMensajeModal('El descuento debe estar entre 0 y 100', 'danger');
        e.preventDefault();
    }
});

// Ocultar alertas después de 10 segundos
window.addEventListener('DOMContentLoaded', () => {
    document.body.classList.add('loaded');
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            alert.classList.remove('show');
            alert.classList.add('hide');
        });
    }, 10000);
});

window.onload = mostrarCarrito;

function mostrarMensajeModal(mensaje, tipo) {
    const modalHtml = `
        <div class="modal fade" id="customAlertModal" tabindex="-1" aria-labelledby="customAlertModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="customAlertModalLabel">Mensaje</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body ${tipo}">
                        ${mensaje}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    const existingModal = document.getElementById('customAlertModal');
    if (existingModal) {
        existingModal.remove();
    }
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const customAlertModal = new bootstrap.Modal(document.getElementById('customAlertModal'));
    customAlertModal.show();
}

document.getElementById('formaPago').addEventListener('change', function () {
    const metodo = this.value;

    if (metodo === 'tarjeta') {
        const modalTarjeta = new bootstrap.Modal(document.getElementById('modalTarjeta'));
        modalTarjeta.show();
    } else if (metodo === 'transferencia') {
        const modalTransferencia = new bootstrap.Modal(document.getElementById('modalTransferencia'));
        modalTransferencia.show();
    }
});

document.querySelectorAll(".btn-metodo-pago").forEach(boton => {
  boton.addEventListener("click", function () {
    const metodo = boton.getAttribute("data-metodo");
    document.getElementById("metodoPagoInput").value = metodo;

    // Opcional: cerrar el modal (si estás usando Bootstrap 5)
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalMetodoPago'));
    modal.hide();
  });
});

document.getElementById("btnConfirmarPago").addEventListener("click", function () {
  document.getElementById("formVenta").submit();
});


