from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
import os
import smtplib
from email.message import EmailMessage
import traceback # Importar para ver trazas de error completas
import threading
import time
from PyPDF2 import PdfReader, PdfWriter

# Importaciones necesarias para manejar fuentes TTF y tablas con ReportLab
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle, Paragraph, HRFlowable # Importar Paragraph para texto en tabla
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # Para estilos de párrafo
from reportlab.lib.units import inch # Para definir anchos en pulgadas
from reportlab.lib.enums import TA_LEFT


# Importaciones de la base de datos (asegúrate de que setup_db esté configurado correctamente)
from setup_db import db, Usuario, Rol, Permiso, RolPermiso, Cliente, Producto, Venta, DetalleVenta, Pago, Factura, Contactanos
import sqlite3 # Mantenido para las funciones que lo usan directamente si es el caso

# Define la ruta de la imagen del logo
LOGO_PATH = os.path.join(os.path.dirname(__file__), 'static', 'images', 'imagen.jpg')

# --- CONFIGURACIÓN DE FUENTES ORBITRON ---
FONT_DIR = os.path.join(os.path.dirname(__file__), 'static', 'fonts')

try:
    pdfmetrics.registerFont(TTFont('Orbitron-Regular', os.path.join(FONT_DIR, 'Orbitron-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('Orbitron-Bold', os.path.join(FONT_DIR, 'Orbitron-Bold.ttf')))
    print("Fuentes Orbitron registradas correctamente para PDF.")
except Exception as e:
    print(f"❌ Error al registrar las fuentes Orbitron para PDF: {e}. Asegúrate de que los archivos .ttf estén en {FONT_DIR}")
    # Si las fuentes no se cargan, ReportLab volverá a usar una fuente predeterminada (como Helvetica).

# Estilos para Paragraph (aunque se usarán en TableStyle en su mayoría para la fuente)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='OrbitronNormal', fontName='Orbitron-Regular', fontSize=10, leading=12))
styles.add(ParagraphStyle(name='OrbitronBold', fontName='Orbitron-Bold', fontSize=11, leading=13))


def encabezado(canvas_obj, doc, titulo):

    # --- COORDENADAS DEL LOGO ---
    # logo_x: Controla la posición HORIZONTAL del logo.
    #         - Aumenta este valor para mover el logo hacia la DERECHA.
    #         - Disminuye este valor para mover el logo hacia la IZQUIERDA.
    # Ajusta la posición del logo para que esté más arriba y no se superponga
    logo_x = 40
    logo_y = 740 
    

    # logo_y: Controla la posición VERTICAL del logo.
    #         - Aumenta este valor para mover el logo hacia ARRIBA.
    #         - Disminuye este valor para mover el logo hacia ABAJO.
    #         Actualmente ajustado a 755 para que el logo sea completamente visible y no se corte.
    # Ajusta la posición de las líneas para que estén por debajo del logo y el título
    line_y1 = 740 # Mantener por debajo del título y logo
    line_y2 = 736 # Mantener en relación con line_y1

    # Logo en la esquina superior izquierda
    if os.path.exists(LOGO_PATH):
        canvas_obj.drawImage(LOGO_PATH, logo_x, logo_y-10, width=60, height=60, mask='auto')
    else:
        print(f"Advertencia: El archivo de logo no se encontró en {LOGO_PATH}")
        canvas_obj.setFont("Orbitron-Regular", 12) # Usa Orbitron si el logo no se carga
        canvas_obj.drawString(logo_x, logo_y + 20, "LOGO NO ENCONTRADO")

    # Título en naranja, usando Orbitron-Bold
    canvas_obj.setFont("Orbitron-Bold", 20)
    canvas_obj.setFillColorRGB(1, 0.5, 0)  # Naranja
    canvas_obj.drawCentredString(320, 760, titulo.title()) # Posición del título

    # Línea decorativa en degradado (simulada con dos líneas)
    canvas_obj.setStrokeColorRGB(1, 0.5, 0)  # Naranja
    canvas_obj.setLineWidth(3)
    canvas_obj.line(40, line_y1-10, 570, line_y1-10) # Primera línea
    canvas_obj.setStrokeColorRGB(0.86, 0.01, 0.01)  # Rojo
    canvas_obj.setLineWidth(1)
    canvas_obj.line(40, line_y2-10, 570, line_y2-10) # Segunda línea

    # Fecha en blanco a la derecha, sin segundos, usando Orbitron-Regular
    canvas_obj.setFont("Orbitron-Regular", 10)
    canvas_obj.setFillColorRGB(1, 1, 1)  # Blanco
    # Formato de fecha/hora sin segundos (%H:%M)
    canvas_obj.drawRightString(570, 760, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Regresa a color negro para el resto del contenido por defecto
    canvas_obj.setFillColorRGB(0, 0, 0)

# Función para formatear moneda (asegurando el formato sin decimales y con punto para miles)
def formatear_moneda(valor):
    try:
        numeric_value = float(valor)
        # Convertir a entero para asegurar que no haya decimales, luego formatear con coma
        # para miles y finalmente reemplazar la coma por un punto.
        formatted_string = f"{int(numeric_value):,}".replace(",", ".")
        return f"${formatted_string}"
    except (ValueError, TypeError):
        return "$0"

def capitalizar(texto):
    return texto.title()

def proteger_pdf(ruta_original, ruta_salida, contraseña):
    try:
        reader = PdfReader(ruta_original)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(user_password=contraseña, owner_password=None, use_128bit=True)

        with open(ruta_salida, 'wb') as f:
            writer.write(f)

        print(f"PDF protegido guardado en: {ruta_salida}")

        # Iniciar temporizador para eliminar el archivo después de 20 minutos
        eliminar_pdf_tras_tiempo(ruta_salida, minutos=20)

    except Exception as e:
        print(f"Error al proteger el PDF: {e}")

def eliminar_pdf_tras_tiempo(ruta, minutos=20):
    def eliminar():
        print(f"[eliminar_pdf_tras_tiempo] Temporizador iniciado: El archivo '{ruta}' se eliminará en {minutos} minutos...")
        time.sleep(minutos * 60)
        try:
            if os.path.exists(ruta):
                os.remove(ruta)
                print(f"[eliminar_pdf_tras_tiempo] PDF eliminado tras {minutos} minutos: {ruta}")
            else:
                print(f"[eliminar_pdf_tras_tiempo] Archivo ya no existe: {ruta}")
        except Exception as e:
            print(f"[eliminar_pdf_tras_tiempo] Error al intentar eliminar el archivo: {e}")

    threading.Thread(target=eliminar, daemon=True).start()


def generar_factura_pdf(id_venta, archivo_salida, vendedor):
    try:
        venta = Venta.query.filter_by(id_venta=id_venta).first()
        cliente = Cliente.query.filter_by(cedula=venta.cedula).first()
        productos = DetalleVenta.query.filter_by(id_venta=id_venta).all()

        doc = SimpleDocTemplate(archivo_salida, pagesize=letter)
        doc.title = f"Factura de Venta #{id_venta}"
        doc.author = "VIKINGO Technology"
        elements = []

        style_orange = ParagraphStyle(
            name='OrbitronBoldOrange',
            fontName='Orbitron-Bold',
            fontSize=12,
            textColor=colors.HexColor('#FF8000'),
            alignment=TA_LEFT,
        )
        style_normal = ParagraphStyle(
            name='OrbitronNormal',
            fontName='Orbitron-Regular',
            fontSize=11,
            textColor=colors.black,
            alignment=TA_LEFT,
        )

        # Datos del cliente y venta
        elements.append(Paragraph(f"<b>Factura de Venta #{id_venta}</b>", style_orange))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"Nombre: {cliente.nombre_completo.title()}", style_normal))
        elements.append(Paragraph(f"Correo: {cliente.correo}", style_normal))
        elements.append(Paragraph(f"Teléfono: {cliente.telefono}", style_normal))
        fecha_venta_dt = venta.fecha_venta
        if isinstance(fecha_venta_dt, str):
            try:
                fecha_venta_dt = datetime.strptime(fecha_venta_dt, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        fecha_str = fecha_venta_dt.strftime('%Y/%m/%d %H:%M') if isinstance(fecha_venta_dt, datetime) else str(fecha_venta_dt)
        elements.append(Paragraph(f"Fecha de Venta: {fecha_str}", style_normal))
        elements.append(Spacer(1, 12))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#FF8000')))
        elements.append(Spacer(1, 8))

        # Tabla de productos
        data = [['Producto', 'Cantidad', 'Precio Unitario', 'Subtotal']]
        for prod in productos:
            producto = Producto.query.get(prod.id_producto)
            descuento_porcentaje = prod.descuento_porcentaje if prod.descuento_porcentaje else 0
            data.append([
                Paragraph(capitalizar(producto.nombre), style_normal),
                str(prod.cantidad),
                formatear_moneda(prod.precio_unitario),
                formatear_moneda(prod.cantidad * prod.precio_unitario)
            ])

        table_col_widths = [2.0*inch, 1.1*inch, 1.5*inch, 1.2*inch]
        table = Table(data, colWidths=table_col_widths, repeatRows=1)
        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FF8000')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Orbitron-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('TOPPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('FONTNAME', (0,1), (-1,-1), 'Orbitron-Regular'),
            ('FONTSIZE', (0,1), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ])
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#FF8000')))
        elements.append(Spacer(1, 8))

        # Totales
        elements.append(Paragraph(f"<b>Subtotal:</b> {formatear_moneda(venta.total)}", style_orange))
        descuento_valor = venta.total - venta.total_con_descuento
        if descuento_valor > 0:
            elements.append(Paragraph(f"<b>Descuento:</b> {formatear_moneda(descuento_valor)} ({descuento_porcentaje}%)", style_orange))
        else:
            elements.append(Paragraph("<b>Descuento:</b> No se aplicó descuento", style_orange))
        elements.append(Paragraph(f"<b>Total:</b> {formatear_moneda(venta.total_con_descuento)}", style_orange))
        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#FF8000')))
        elements.append(Spacer(1, 8))

        # Datos de pago y vendedor
        pago = Pago.query.filter_by(id_venta=id_venta).first()
        total_productos = len(productos)
        elements.append(Paragraph(f"<b>Forma de Pago:</b> {pago.metodo_pago}", style_normal))
        elements.append(Paragraph(f"<b>ATENDIDO POR:</b> {vendedor}", style_normal))
        elements.append(Paragraph(f"<b>total producto comprados:</b> {total_productos}", style_normal))
        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#FF8000')))
        elements.append(Spacer(1, 8))

        # Mensaje de agradecimiento
        mensaje = (
            "Gracias por comprar en Vikingo Technology.<br/>"
            "Esperamos que disfrutes tu producto. Si tienes dudas o reclamos,<br/>"
            "contáctanos a vikingotic@gmail.com o al 300-123-4567.<br/>"
            "¡Recuerda que lo barato sale caro, y lo Vikingo dura años!"
        )
        style_gracias = ParagraphStyle(
            name='Gracias',
            fontName='Orbitron-Regular',
            fontSize=10,
            textColor=colors.black,
            alignment=1,  # 1 = TA_CENTER
            leading=14,
        )
        elements.append(Paragraph(mensaje, style_gracias))

        doc.build(
            elements,
            onFirstPage=lambda canvas, doc: encabezado(canvas, doc, "Factura de Venta"),
            onLaterPages=lambda canvas, doc: encabezado(canvas, doc, "Factura de Venta")
        )
        print("Factura generada correctamente (con estilo unificado y paginación automática).")
        eliminar_pdf_tras_tiempo(archivo_salida, minutos=20)
    except PermissionError as e:
        print(f"❌ Error de Permiso al generar la factura: {e}.")
        traceback.print_exc()
    except Exception as e:
        print(f"Error al generar la factura: {e}")
        traceback.print_exc()

# Genera un PDF con el listado de productos actuales
def generar_informe_productos_pdf(archivo_salida, productos, fecha_inicio, fecha_fin):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT

    doc = SimpleDocTemplate(archivo_salida, pagesize=letter)
    doc.title = "Informe de Productos"
    doc.author = "VIKINGO Technology"
    elements = []

    style_orange = ParagraphStyle(
        name='OrbitronBoldOrange',
        fontName='Orbitron-Bold',
        fontSize=12,
        textColor=colors.HexColor('#FF8000'),
        alignment=TA_LEFT,
    )
    style_normal = ParagraphStyle(
        name='OrbitronNormal',
        fontName='Orbitron-Regular',
        fontSize=10,
        textColor=colors.black,
        alignment=TA_LEFT,
    )

    elements.append(Paragraph("<b>Informe de Productos</b>", style_orange))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#FF8000')))
    elements.append(Spacer(1, 8))

    # Información de fecha
    if fecha_inicio and fecha_fin:
        fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d') if isinstance(fecha_inicio, datetime) else str(fecha_inicio)
        fecha_fin_str = fecha_fin.strftime('%Y-%m-%d') if isinstance(fecha_fin, datetime) else str(fecha_fin)
        elements.append(Paragraph(f"Fecha de Inicio: {fecha_inicio_str}", style_normal))
        elements.append(Paragraph(f"Fecha de Fin: {fecha_fin_str}", style_normal))
        elements.append(Spacer(1, 8))

    # Encabezados de la tabla
    data = [[
        'ID', 'Nombre', 'Cantidad', 'Ventas', 'Vendidos', 'Total Ganado'
    ]]
    total_ventas = 0
    total_productos = 0
    total_ganado = 0
    for p in productos:
        data.append([
            str(p['id_producto']),
            Paragraph(capitalizar(p['nombre']), style_normal),
            str(p.get('stock', '')),
            str(p.get('ventas', '')),
            str(p.get('vendidos', '')),
            formatear_moneda(p.get('total_ganado', 0))
        ])
        total_ventas += p.get('ventas', 0)
        total_productos += p.get('stock', 0)
        total_ganado += p.get('total_ganado', 0)

    table_col_widths = [0.7*inch, 1.9*inch, 0.9*inch, 0.9*inch, 1.0*inch, 1.5*inch]
    table = Table(data, colWidths=table_col_widths, repeatRows=1)
    table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FF8000')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Orbitron-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('TOPPADDING', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
        ('FONTNAME', (0,1), (-1,-1), 'Orbitron-Regular'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ])
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 16))
    elements.append(Paragraph(f"<b>Total Ventas:</b>{total_ventas}", style_orange))
    elements.append(Paragraph(f"<b>Total Productos:</b> {total_productos}", style_orange))
    elements.append(Paragraph(f"<b>Total Ganado:</b> {formatear_moneda(total_ganado)}", style_orange))
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#FF8000')))
    elements.append(Spacer(1, 8))

    doc.build(
        elements,
        onFirstPage=lambda canvas, doc: encabezado(canvas, doc, "Informe de Productos"),
        onLaterPages=lambda canvas, doc: encabezado(canvas, doc, "Informe de Productos")
    )
    eliminar_pdf_tras_tiempo(archivo_salida, minutos=20)
    print("Informe de productos generado correctamente.")

def generar_historial_cliente_pdf(cedula, archivo_salida):
    try:
        cliente = Cliente.query.filter_by(cedula=cedula).first()
        if not cliente:
            print("Cliente no encontrado.")
            return

        compras = Venta.query.filter_by(cedula=cedula).order_by(Venta.fecha_venta.desc()).all()
        if not compras:
            print("No se encontraron compras para este cliente.")
            return


        # --- USAR PLATYPUS PARA PAGINACIÓN AUTOMÁTICA ---
        doc = SimpleDocTemplate(archivo_salida, pagesize=letter)
        doc.title = f"Historial de Compras de {cliente.nombre_completo.title()}"
        doc.author = "VIKINGO Technology"
        elements = []

        style_orange = ParagraphStyle(
            name='OrbitronBoldOrange',
            fontName='Orbitron-Bold',
            fontSize=12,
            textColor=colors.HexColor('#FF8000'),
            alignment=TA_LEFT,
        )
        style_normal = ParagraphStyle(
            name='OrbitronNormal',
            fontName='Orbitron-Regular',
            fontSize=11,
            textColor=colors.black,
            alignment=TA_LEFT,
        )

        # Datos del cliente
        elements.append(Paragraph(f"Nombre: {cliente.nombre_completo.title()}", style_orange))
        elements.append(Paragraph(f"Correo: {cliente.correo}", style_normal))
        elements.append(Paragraph(f"Teléfono: {cliente.telefono}", style_normal))
        now = datetime.now()
        current_date_time_str = now.strftime("%d/%m/%Y %H:%M")
        elements.append(Paragraph(f"Fecha y Hora de Generación: {current_date_time_str}", style_normal))
        elements.append(Spacer(1, 12))

        # Tabla de historial
        data = [['Producto', 'Cantidad', 'Precio Unit.', 'Total Prod.', 'Subtotal']] # Encabezados de la tabla
        historial = []
        total_historial = [] #esto lo hice para que se guaradaran todas las ventas para sacar el total gastado, nose de que otra forma ahcerlo para no complicarme tanto
        for venta in compras:
            detalles = DetalleVenta.query.filter_by(id_venta=venta.id_venta).all()
            for detalle in detalles:
                producto = Producto.query.get(detalle.id_producto)
                if producto:
                    historial.append({
                        'id_venta': venta.id_venta,
                        'fecha': venta.fecha_venta,
                        'producto': producto.nombre,
                        'cantidad': detalle.cantidad,
                        'precio_unit': detalle.precio_unitario,
                        'subtotal': detalle.subtotal,
                        'total': venta.total_con_descuento
                    })
            fecha_raw = venta.fecha_venta
            if isinstance(fecha_raw, str):
                try:
                    fecha = datetime.strptime(fecha_raw, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    fecha = fecha_raw
            else:
                fecha = fecha_raw
            fecha_formateada = fecha.strftime("%d/%m/%Y") if isinstance(fecha, datetime) else str(fecha)
            # Usar Paragraph para producto (permite salto de línea)
            elements.append(Spacer(1, 8))  # Espacio entre encabezado y tabla
            elements.append(Paragraph(f"ID de la venta: {venta.id_venta}", style_orange))
            elements.append(Paragraph(f"Fecha: {fecha_formateada}", style_normal))
            
            for item in historial:
                data.append([
                    Paragraph(capitalizar(item['producto']), style_normal),
                    str(item['cantidad']),
                    formatear_moneda(item['precio_unit']),
                    formatear_moneda(item['precio_unit'] * item['cantidad']),  
                    formatear_moneda(item['subtotal'])
                    ])
            elements.append(Spacer(1, 12))
            # Añadir tabla de la venta actual
            table_col_widths = [1.8*inch, 1.0*inch, 1.2*inch, 1.2*inch, 1.2*inch]
            table = Table(data, colWidths=table_col_widths, repeatRows=1)
            table_style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FF8000')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Orbitron-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 11),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,0), 10),
                ('TOPPADDING', (0,0), (-1,0), 10),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
                ('FONTNAME', (0,1), (-1,-1), 'Orbitron-Regular'),
                ('FONTSIZE', (0,1), (-1,-1), 10),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Descuento: {detalle.descuento_porcentaje}%", style_orange))
            descuento_valor = venta.total - venta.total_con_descuento
            elements.append(Paragraph(f"Ahorrado: {formatear_moneda(descuento_valor)}", style_orange))
            elements.append(Paragraph(f"Total: {formatear_moneda(venta.total_con_descuento)}", style_orange))
            elements.append(Spacer(1, 12))
            # Línea divisoria naranja debajo del total de la venta
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#FF8000')))
            elements.append(Spacer(1, 12))
            
            data = [['Producto', 'Cantidad', 'Precio Unit.', 'Total Prod.', 'Subtotal']] # Reiniciar datos de la tabla para la siguiente venta
            total_historial.append(historial)
            historial = [] #vacio la lista para la siguiente venta
            

        # Total gastado
        # Aplana la lista de listas en una sola lista de diccionarios
        todos_los_items = [item for sublist in total_historial for item in sublist]
        total_gastado = sum(item['subtotal'] for item in todos_los_items)
        cantidad_compras = len(compras)
        elements.append(Paragraph(f"<b>Total Gastado: {formatear_moneda(total_gastado)}</b>", style_orange))
        elements.append(Paragraph(f"<b>Cantidad de Compras: {cantidad_compras}</b>", style_orange))

        doc.build(
            elements,
            onFirstPage=lambda canvas, doc: encabezado(canvas, doc, "Historial de Cliente"),
            onLaterPages=lambda canvas, doc: encabezado(canvas, doc, "Historial de Cliente")
        )
        eliminar_pdf_tras_tiempo(archivo_salida, minutos=20)
        print("Historial del cliente generado correctamente (con paginación y celdas ajustadas).")
    except Exception as e:
        print(f"Error al generar el historial del cliente: {e}")
        traceback.print_exc()
    

# def generar_informe_producto_pdf(fecha_inicio, fecha_fin, archivo_salida):
#     conn = sqlite3.connect('database.db')
#     if conn is None:
#         print("No se pudo conectar a la base de datos.")
#         return

#     try:
#         cursor = conn.cursor()
#         cursor.execute('''
#             SELECT p.nombre, SUM(dv.cantidad) AS total_vendido, SUM(dv.subtotal) AS total_generado
#             FROM Detalle_venta dv
#             JOIN Producto p ON dv.id_producto = p.id_producto
#             JOIN Venta v ON dv.id_venta = v.id_venta
#             WHERE v.fecha_venta BETWEEN ? AND ?
#             GROUP BY p.nombre
#             ORDER BY total_vendido DESC
#         ''', (fecha_inicio, fecha_fin))
#         productos = cursor.fetchall()

#         c = canvas.Canvas(archivo_salida, pagesize=letter)
#         width, height = letter
#         encabezado(c, "Informe de Ventas por Producto")
#         y = height - 150

#         # Encabezados de la tabla
#         data = [['Producto', 'Cantidad Vendida', 'Total Generado']]
#         for p in productos:
#             data.append([
#                 capitalizar(p["nombre"]),
#                 str(p["total_vendido"]),
#                 formatear_moneda(p["total_generado"])
#             ])

#         table_col_widths = [2.5*inch, 1.5*inch, 1.5*inch] # Ajusta anchos de columna

#         table = Table(data, colWidths=table_col_widths)

#         table_style = TableStyle([
#             ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FF8000')),
#             ('TEXTCOLOR', (0,0), (-1,0), colors.white),
#             ('FONTNAME', (0,0), (-1,0), 'Orbitron-Bold'),
#             ('FONTSIZE', (0,0), (-1,0), 11),
#             ('ALIGN', (0,0), (-1,-1), 'CENTER'),
#             ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
#             ('BOTTOMPADDING', (0,0), (-1,0), 10),
#             ('TOPPADDING', (0,0), (-1,0), 10),
#             ('BACKGROUND', (0,1), (-1,-1), colors.white),
#             ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
#             ('FONTNAME', (0,1), (-1,-1), 'Orbitron-Regular'),
#             ('FONTSIZE', (0,1), (-1,-1), 10),
#             ('GRID', (0,0), (-1,-1), 1, colors.black),
#             ('LEFTPADDING', (0,0), (-1,-1), 5),
#             ('RIGHTPADDING', (0,0), (-1,-1), 5),
#         ])
#         table.setStyle(table_style)

#         table_width, table_height = table.wrapOn(c, width, height)
#         # Para centrar la tabla: (width - table_width) / 2
#         table_x_position = (width - table_width) / 2
#         table.drawOn(c, table_x_position, y - table_height - 10)
#         y -= table_height + 20

#         c.save()
#         print("Informe de productos generado.")
#     except PermissionError as e: # Captura el error específico de permisos
#         print(f"❌ Error de Permiso al generar el informe de productos: {e}. Asegúrate de que el archivo PDF no esté abierto en otra aplicación y que tengas permisos de escritura.")
#         traceback.print_exc()
#     except Exception as e:
#         print(f"Error al generar informe de productos: {e}")
#         traceback.print_exc()
#     finally:
#         conn.close()

# def generar_informe_cliente_pdf(fecha_inicio, fecha_fin, archivo_salida):
#     conn = get_connection()
#     if conn is None:
#         print("No se pudo conectar a la base de datos.")
#         return

#     try:
#         cursor = conn.cursor()
#         cursor.execute('''
#             SELECT c.nombre_completo, c.correo, COUNT(v.id_venta) AS compras, SUM(v.total_con_descuento) AS gastado
#             FROM Cliente c
#             JOIN Venta v ON c.cedula = v.cedula
#             WHERE v.fecha_venta BETWEEN ? AND ?
#             GROUP BY c.cedula
#             ORDER BY gastado DESC
#         ''', (fecha_inicio, fecha_fin))
#         clientes = cursor.fetchall()

#         c = canvas.Canvas(archivo_salida, pagesize=letter)
#         width, height = letter
#         encabezado(c, "Informe de Ventas por Cliente")
#         y = height - 150

#         # Encabezados de la tabla
#         data = [['Cliente', 'Correo', 'Compras', 'Total Gastado']]
#         for cli in clientes:
#             data.append([
#                 capitalizar(cli["nombre_completo"]),
#                 cli["correo"],
#                 str(cli["compras"]),
#                 formatear_moneda(cli["gastado"])
#             ])
        
#         table_col_widths = [2.0*inch, 2.0*inch, 1.0*inch, 1.2*inch] # Ajusta anchos de columna

#         table = Table(data, colWidths=table_col_widths)

#         table_style = TableStyle([
#             ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FF8000')),
#             ('TEXTCOLOR', (0,0), (-1,0), colors.white),
#             ('FONTNAME', (0,0), (-1,0), 'Orbitron-Bold'),
#             ('FONTSIZE', (0,0), (-1,0), 11),
#             ('ALIGN', (0,0), (-1,-1), 'CENTER'),
#             ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
#             ('BOTTOMPADDING', (0,0), (-1,0), 10),
#             ('TOPPADDING', (0,0), (-1,0), 10),
#             ('BACKGROUND', (0,1), (-1,-1), colors.white),
#             ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
#             ('FONTNAME', (0,1), (-1,-1), 'Orbitron-Regular'),
#             ('FONTSIZE', (0,1), (-1,-1), 10),
#             ('GRID', (0,0), (-1,-1), 1, colors.black),
#             ('LEFTPADDING', (0,0), (-1,-1), 5),
#             ('RIGHTPADDING', (0,0), (-1,-1), 5),
#         ])
#         table.setStyle(table_style)

#         table_width, table_height = table.wrapOn(c, width, height)
#         # Para centrar la tabla: (width - table_width) / 2
#         table_x_position = (width - table_width) / 2
#         table.drawOn(c, table_x_position, y - table_height - 10)
#         y -= table_height + 20


#         c.save()
#         print("Informe de clientes generado.")
#     except PermissionError as e: # Captura el error específico de permisos
#         print(f"❌ Error de Permiso al generar el informe de clientes: {e}. Asegúrate de que el archivo PDF no esté abierto en otra aplicación y que tengas permisos de escritura.")
#         traceback.print_exc()
#     except Exception as e:
#         print(f"Error al generar informe de clientes: {e}")
#         traceback.print_exc()
#     finally:
#         conn.close()

# ---------------- ENVÍO DE PDF POR CORREO ----------------
def enviar_pdf_por_correo(destinatario, asunto, cuerpo, archivo_pdf):
    remitente = "vikingotic@gmail.com"
    contraseña = "moao fznw jaue uwdx"   

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario
    msg.set_content(cuerpo)
    
    if not archivo_pdf == "nohay":
        if os.path.exists(archivo_pdf):
            with open(archivo_pdf, 'rb') as f:
                contenido = f.read()
                msg.add_attachment(contenido, maintype='application', subtype='pdf', filename=os.path.basename(archivo_pdf))
        else:
            print("El archivo PDF no existe.")
            return

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, contraseña)
            smtp.send_message(msg)
        print("✅ PDF enviado a", destinatario)
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")
        traceback.print_exc()