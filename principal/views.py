from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_GET
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from uuid import uuid4
import pymysql
import requests
import uuid
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Trabajador, Producto, Pedido
from django.shortcuts import render, redirect, get_object_or_404

# Transbank (Webpay Plus)
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType




@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

def inicio(request):
    return render(request, 'inicio.html')

def login_view(request):
    if request.method == 'POST':
        correo = request.POST.get('username')
        clave = request.POST.get('password')

        connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id_usuario, nombre_usuario, es_cliente
            FROM Usuario
            WHERE correo_usuario = %s AND clave_usuario = %s
        """, (correo, clave))
        usuario = cursor.fetchone()
        connection.close()

        if usuario:
            request.session['usuario_id'] = usuario[0]
            request.session['usuario_nombre'] = usuario[1]
            request.session['es_b2b'] = 'N' if usuario[2] == 'S' else 'S'
            return redirect('inicio')
        else:
            messages.error(request, "Credenciales incorrectas.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('inicio')

def registro_view(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        rut = request.POST.get('rut')
        correo = request.POST.get('correo')
        clave = request.POST.get('clave')
        confirmar = request.POST.get('confirmar')
        tipo = request.POST.get('tipo')  # cliente o empresa

        if not correo.endswith('@gmail.com') and not correo.endswith('@hotmail.com'):
            messages.error(request, "El correo debe ser @gmail.com o @hotmail.com")
        elif clave != confirmar:
            messages.error(request, "Las contraseñas no coinciden.")
        else:
            connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
            cursor = connection.cursor()

            genero = 'N'
            fecha_nacimiento = '2000-01-01'
            es_cliente = 'S' if tipo == 'cliente' else 'N'
            rol_id = '1'
            rol_nombre = 'cliente'

            try:
                cursor.execute("""
                    INSERT INTO Usuario (
                        id_usuario, nombre_usuario, correo_usuario, genero_usuario,
                        fecha_nacimiento, clave_usuario, es_cliente, rut_empresa, razon_social
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    rut, nombre, correo, genero, fecha_nacimiento,
                    clave, es_cliente, None if tipo == 'cliente' else rut,  
                    None if tipo == 'cliente' else nombre  
                ))

                
                connection.commit()
                messages.success(request, "Registro exitoso.")
                return redirect('login')
            except Exception as e:
                messages.error(request, f"Error en el registro: {str(e)}")
            finally:
                connection.close()
    return render(request, 'registro.html')

def catalogo_view(request):
    if 'usuario_id' not in request.session:
        return redirect('login')

    usuario_id = request.session['usuario_id']

    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='autoparts'
    )
    cursor = connection.cursor()

    # Productos para el catálogo
    cursor.execute("""
    SELECT id_producto, nombre_producto, descripcion_producto, precio_b2b, precio_b2c, imagen_producto 
    FROM Producto
""")
    productos = cursor.fetchall()

    # Obtener carrito y calcular totales
    cursor.execute("SELECT id_carrito FROM Carrito WHERE Usuario_id_usuario = %s", (usuario_id,))
    carrito = cursor.fetchone()

    carrito_items = []
    total = 0

    if carrito:
        carrito_id = carrito[0]
        cursor.execute("""
            SELECT ci.id_item, p.nombre_producto, ci.cantidad, p.precio_b2c
            FROM CarritoItem ci
            JOIN Producto p ON ci.Producto_id_producto = p.id_producto
            WHERE ci.Carrito_id_carrito = %s
        """, (carrito_id,))
        items = cursor.fetchall()

        for item in items:
            id_item, nombre, cantidad, precio = item
            subtotal = cantidad * precio
            carrito_items.append({
                'id_item': id_item,
                'nombre_producto': nombre,
                'cantidad': cantidad,
                'subtotal': subtotal
            })
            total += subtotal

    connection.close()

    context = {
        'productos': productos,
        'carrito_items': carrito_items,
        'total': total,
        'es_b2b': request.session.get('es_b2b') == 'S'
    }

    return render(request, 'catalogo.html', context)

@csrf_exempt
def actualizar_item(request):
    if request.method == 'POST':
        # Lógica para actualizar cantidad del ítem del carrito
        return JsonResponse({'success': True})

def ir_al_pago(request):
    return HttpResponse("Página de pago simulada (B2C)")

@csrf_exempt
def eliminar_item(request):
    if 'usuario_id' not in request.session:
        return redirect('login')

    id_item = request.POST.get('id_item')

    connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM CarritoItem WHERE id_item = %s", (id_item,))
        connection.commit()
    except Exception as e:
        print("Error al eliminar item:", e)
    finally:
        connection.close()

    return redirect('catalogo')

@csrf_exempt
def agregar_al_carrito(request):
    if request.method == 'POST' and 'usuario_id' in request.session:
        usuario_id = request.session['usuario_id']
        producto_id = request.POST.get('id_producto')
        cantidad = int(request.POST.get('cantidad', 1))

        connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
        cursor = connection.cursor()

        cursor.execute("SELECT id_carrito FROM Carrito WHERE Usuario_id_usuario = %s", (usuario_id,))
        carrito = cursor.fetchone()

        if not carrito:
            cursor.execute("INSERT INTO Carrito (id_carrito, Usuario_id_usuario, fecha_creacion) VALUES (UUID(), %s, NOW())", (usuario_id,))
            connection.commit()
            cursor.execute("SELECT id_carrito FROM Carrito WHERE Usuario_id_usuario = %s", (usuario_id,))
            carrito = cursor.fetchone()

        id_carrito = carrito[0]

        # Verificar si el producto ya está en el carrito
        cursor.execute("""
            SELECT id_item, cantidad FROM CarritoItem 
            WHERE Carrito_id_carrito = %s AND Producto_id_producto = %s
        """, (id_carrito, producto_id))
        item = cursor.fetchone()

        if item:
            nueva_cantidad = item[1] + cantidad
            cursor.execute("UPDATE CarritoItem SET cantidad = %s WHERE id_item = %s", (nueva_cantidad, item[0]))
        else:
            cursor.execute("""
                INSERT INTO CarritoItem (Carrito_id_carrito, Producto_id_producto, cantidad)
                VALUES (%s, %s, %s)
            """, (id_carrito, producto_id, cantidad))

        # Disminuir el stock del producto
        cursor.execute("UPDATE Producto SET stock = stock - %s WHERE id_producto = %s", (cantidad, producto_id))

        connection.commit()
        connection.close()

        return redirect('catalogo')


def obtener_carrito(usuario_id):
    connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
    cursor = connection.cursor()
    cursor.execute("""
        SELECT ci.id_item, p.nombre_producto, ci.cantidad, p.precio_b2c
        FROM CarritoItem ci
        JOIN Producto p ON ci.Producto_id_producto = p.id_producto
        JOIN Carrito c ON ci.Carrito_id_carrito = c.id_carrito
        WHERE c.Usuario_id_usuario = %s
    """, (usuario_id,))
    carrito_items = cursor.fetchall()
    connection.close()
    return carrito_items

def generar_factura(request):
    usuario_id = request.session['usuario_id']
    connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
    cursor = connection.cursor()

    try:
        # Obtener el carrito del usuario
        cursor.execute("SELECT id_carrito FROM Carrito WHERE Usuario_id_usuario = %s", (usuario_id,))
        carrito = cursor.fetchone()
        factura_items = []
        total = 0

        if not carrito:
            messages.error(request, "No tienes productos en el carrito.")
            return redirect('catalogo')

        carrito_id = carrito[0]

        # Obtener productos del carrito
        cursor.execute("""
            SELECT p.id_producto, p.nombre_producto, ci.cantidad, p.precio_b2b, p.stock
            FROM CarritoItem ci
            JOIN Producto p ON ci.Producto_id_producto = p.id_producto
            WHERE ci.Carrito_id_carrito = %s
        """, (carrito_id,))
        items = cursor.fetchall()
        items = cursor.fetchall()

        if not items:
            messages.error(request, "Tu carrito está vacío. No se puede generar una factura.")
            return redirect('catalogo')  



        # Verificar stock
        for id_prod, nombre, cantidad, precio, stock in items:
            if cantidad > stock:
                messages.error(request, f"No hay suficiente stock para '{nombre}'. Stock disponible: {stock}.")
                connection.close()
                return redirect('catalogo')

        # Crear la factura
        id_factura = str(uuid4())
        for id_prod, nombre, cantidad, precio, stock in items:
            subtotal = cantidad * precio
            factura_items.append({
                'id_producto': id_prod,
                'nombre_producto': nombre,
                'cantidad': cantidad,
                'precio': precio,
                'subtotal': subtotal
            })
            total += subtotal

        cursor.execute("""
            INSERT INTO Factura (id_factura, Usuario_id_usuario, total, estado, fecha, fecha_emision)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
        """, (id_factura, usuario_id, total, 'pendiente'))

        connection.commit()  # IMPORTANTE: confirmar la factura antes de los detalles

        # Insertar los detalles
        for item in factura_items:
            cursor.execute("""
                INSERT INTO DetalleFactura (id_factura, id_producto, nombre_producto, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                id_factura,
                item['id_producto'],
                item['nombre_producto'],
                item['cantidad'],
                item['precio'],
                item['subtotal']
            ))

            # Descontar stock
            cursor.execute("""
                UPDATE Producto
                SET stock = stock - %s
                WHERE id_producto = %s
            """, (item['cantidad'], item['id_producto']))

        # Vaciar el carrito
        cursor.execute("DELETE FROM CarritoItem WHERE Carrito_id_carrito = %s", (carrito_id,))
        connection.commit()

    except Exception as e:
        connection.rollback()
        messages.error(request, f"Error al generar la factura: {e}")
    finally:
        connection.close()

    return render(request, 'factura.html', {
        'factura': factura_items,
        'total': total,
        'empresa': (request.session.get('usuario_nombre'), request.session.get('usuario_id'))
    })



def enviar_factura_email(request):
    if request.method == 'POST' and 'usuario_id' in request.session:
        usuario_id = request.session['usuario_id']

        connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
        cursor = connection.cursor()

        cursor.execute("SELECT correo_usuario FROM Usuario WHERE id_usuario = %s", (usuario_id,))
        result = cursor.fetchone()
        connection.close()

        if result:
            correo_destino = result[0]
            asunto = "Factura Proforma - AutoParts"
            mensaje = "Estimado cliente,\n\nAdjuntamos su factura proforma con los detalles del pedido.\n\nSaludos,\nAutoParts"
            try:
                send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [correo_destino])
                messages.success(request, "Factura enviada al correo exitosamente.")
            except Exception as e:
                messages.error(request, f"No se pudo enviar el correo: {e}")
        else:
            messages.error(request, "No se encontró el correo del usuario.")
        return redirect('generar_factura')
    else:
        return redirect('inicio')
    
def perfil_view(request):
    usuario_id = request.session['usuario_id']

    connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
    cursor = connection.cursor()

    # Datos del usuario o empresa
    cursor.execute("""
        SELECT nombre_usuario, correo_usuario, genero_usuario, fecha_nacimiento,
               rut_empresa, razon_social
        FROM Usuario
        WHERE id_usuario = %s
    """, (usuario_id,))
    user_data = cursor.fetchone()
    datos = {
        'nombre': user_data[0],
        'correo': user_data[1],
        'genero': user_data[2],
        'fecha_nacimiento': user_data[3],
        'rut_empresa': user_data[4],
        'razon_social': user_data[5]
    }

    cursor.execute("""
    SELECT df.nombre_producto, df.cantidad, df.precio_unitario, df.subtotal, f.fecha_emision
    FROM DetalleFactura df
    JOIN Factura f ON df.id_factura = f.id_factura
    WHERE f.Usuario_id_usuario = %s
    ORDER BY f.fecha_emision DESC
    """, (usuario_id,))

    compras_raw = cursor.fetchall()

    compras = [
        {
            'nombre_producto': row[0],
            'cantidad': row[1],
            'precio': row[2],
            'subtotal': row[3],
            'fecha': row[4]
        }
        for row in compras_raw
    ]

    # Estado del pedido actual
    cursor.execute("""
        SELECT id_carrito, estado
        FROM Carrito
        WHERE Usuario_id_usuario = %s
        ORDER BY fecha_creacion DESC
        LIMIT 1
    """, (usuario_id,))
    estado_pedido = cursor.fetchone()

    connection.close()

    return render(request, 'perfil.html', {
    'usuario': datos,
    'historial': compras,
    'estado_pedido': estado_pedido
})


def checkout_b2c_view(request):
    usuario_id = request.session['usuario_id']

    connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
    cursor = connection.cursor()

    # Obtener carrito
    cursor.execute("SELECT id_carrito FROM Carrito WHERE Usuario_id_usuario = %s", (usuario_id,))
    carrito = cursor.fetchone()

    if not carrito:
        connection.close()
        return redirect('catalogo')

    carrito_id = carrito[0]
    cursor.execute("""
        SELECT p.nombre_producto, ci.cantidad, p.precio_b2c
        FROM CarritoItem ci
        JOIN Producto p ON ci.Producto_id_producto = p.id_producto
        WHERE ci.Carrito_id_carrito = %s
    """, (carrito_id,))
    items = cursor.fetchall()

    productos = []
    total = 0
    for nombre, cantidad, precio in items:
        subtotal = cantidad * precio
        productos.append({
            'nombre_producto': nombre,
            'cantidad': cantidad,
            'precio': precio,
            'subtotal': subtotal
        })
        total += subtotal

    connection.close()

    context = {
        'productos': productos,
        'total': total
    }

    return render(request, 'checkout_b2c.html', context)

def ir_al_pago(request):
    usuario_id = request.session['usuario_id']
    
    connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id_carrito FROM Carrito WHERE Usuario_id_usuario = %s
    """, (usuario_id,))
    carrito = cursor.fetchone()

    resumen = []
    total = 0

    if carrito:
        carrito_id = carrito[0]
        cursor.execute("""
            SELECT p.nombre_producto, ci.cantidad, p.precio_b2c
            FROM CarritoItem ci
            JOIN Producto p ON ci.Producto_id_producto = p.id_producto
            WHERE ci.Carrito_id_carrito = %s
        """, (carrito_id,))
        productos = cursor.fetchall()

        for nombre, cantidad, precio in productos:
            subtotal = cantidad * precio
            resumen.append({
                'nombre': nombre,
                'cantidad': cantidad,
                'precio': precio,
                'subtotal': subtotal
            })
            total += subtotal

    connection.close()

    return render(request, 'pago_b2c.html', {
        'resumen': resumen,
        'total': total
    })
    
@csrf_exempt
def procesar_pago_b2c(request):
    if request.method == 'POST':
        metodo_envio = request.POST.get('metodo_envio')
        direccion = request.POST.get('direccion')
        ciudad = request.POST.get('ciudad')
        telefono = request.POST.get('telefono')

        precio_envio = 0  # por defecto

        if metodo_envio == 'envio':
            try:
                import requests

                headers = {
                    "Ocp-Apim-Subscription-Key": "Francisca.21",
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache"
                }

                payload = {
                    "originCountyCode": "STGO",
                    "destinationCountyCode": ciudad.upper()[:4],  # adaptarlo según comuna
                    "package": {
                        "weight": "1",
                        "height": "10",
                        "width": "10",
                        "length": "10"
                    },
                    "productType": 3,
                    "contentType": 1,
                    "declaredWorth": "20000",
                    "deliveryTime": 0
                }

                response = requests.post(
                    "https://testservices.wschilexpress.com/rating/api/v1.0/rates/courier",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    datos = response.json()
                    precio_envio = datos['rates'][0]['service']['price']  # ajustar según respuesta exacta
                else:
                    print("Error Chilexpress:", response.text)

            except Exception as e:
                print("Excepción al consultar Chilexpress:", e)

        # Simulación pago MercadoLibre
        messages.success(request, f"Compra realizada. Envío: ${precio_envio} CLP. Recibirás un correo.")

        # Vaciar carrito
        usuario_id = request.session['usuario_id']
        connection = pymysql.connect(host='localhost', user='root', password='', db='autoparts')
        cursor = connection.cursor()

        cursor.execute("SELECT id_carrito FROM Carrito WHERE Usuario_id_usuario = %s", (usuario_id,))
        carrito = cursor.fetchone()

        if carrito:
            cursor.execute("DELETE FROM CarritoItem WHERE Carrito_id_carrito = %s", (carrito[0],))
            connection.commit()

        connection.close()
        return redirect('catalogo')

    return redirect('catalogo')

@require_GET
def api_costo_envio(request):
    ciudad = request.GET.get('ciudad', '')
    direccion = request.GET.get('direccion', '')
    precio_envio = 0

    if ciudad and direccion:
        try:
            headers = {
                "Ocp-Apim-Subscription-Key": "Francisca.21",
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            }

            payload = {
                "originCountyCode": "STGO",
                "destinationCountyCode": ciudad.upper()[:4],
                "package": {
                    "weight": "1",
                    "height": "10",
                    "width": "10",
                    "length": "10"
                },
                "productType": 3,
                "contentType": 1,
                "declaredWorth": "20000",
                "deliveryTime": 0
            }

            response = requests.post(
                "https://testservices.wschilexpress.com/rating/api/v1.0/rates/courier",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                datos = response.json()
                precio_envio = datos['rates'][0]['service']['price']
        except Exception as e:
            print("Error al consultar Chilexpress:", e)

    return JsonResponse({'precio_envio': precio_envio})

"""  """
@csrf_exempt
def iniciar_pago_webpay(request):
    if not request.session.get("carrito"):
        return HttpResponse("No hay productos para pagar.")

    carrito = request.session["carrito"]
    total = sum(item["subtotal"] for item in carrito.values())

    if total <= 0:
        return HttpResponse("No hay monto para pagar.")

    buy_order = f"ORD-{uuid4().hex[:10]}"
    session_id = str(uuid4())
    return_url = request.build_absolute_uri(reverse("webpay_retorno"))

    tx = Transaction(WebpayOptions(
        commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
        api_key=IntegrationApiKeys.WEBPAY,
        integration_type=IntegrationType.TEST
    ))

    try:
        response = tx.create(buy_order, session_id, total, return_url)
        request.session["buy_order"] = buy_order
        request.session["total_pagado"] = total
        return redirect(response["url"] + "?token_ws=" + response["token"])
    except Exception as e:
        return HttpResponse(f"Error al iniciar transacción: {e}")

@csrf_exempt
def retorno_pago_webpay(request):
    token = request.GET.get("token_ws")
    if not token:
        return HttpResponse("Transacción cancelada o token no recibido.")

    tx = Transaction(WebpayOptions(
        commerce_code=IntegrationCommerceCodes.WEBPAY_PLUS,
        api_key=IntegrationApiKeys.WEBPAY,
        integration_type=IntegrationType.TEST
    ))

    try:
        response = tx.commit(token)
        if response["status"] == "AUTHORIZED":
            usuario_id = request.session.get("usuario_id")
            total = request.session.get("total_pagado")
            carrito = request.session.get("carrito", {})

            factura = Factura.objects.create(
                Usuario_id_usuario=usuario_id,
                total=total,
                estado="Pagado",
                fecha=datetime.date.today(),
                fecha_emision=datetime.date.today()
            )

            for item in carrito.values():
                DetalleFactura.objects.create(
                    id_factura=factura,
                    id_producto_id=item["id_producto"],
                    nombre_producto=item["nombre"],
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio"],
                    subtotal=item["subtotal"]
                )

            request.session["carrito"] = {}
            request.session["ultima_factura_id"] = factura.id_factura

            return redirect("boleta")
        else:
            return HttpResponse(f"Transacción fallida: {response['status']}")
    except Exception as e:
        return HttpResponse(f"Error al confirmar transacción: {e}")
    
def boleta(request):
    id_factura = request.session.get("ultima_factura_id")
    if not id_factura:
        return HttpResponse("No se encontró una factura reciente.")
    try:
        factura = Factura.objects.get(pk=id_factura)
        detalles = DetalleFactura.objects.filter(id_factura=factura)
        return render(request, "boleta.html", {"factura": factura, "detalles": detalles})
    except:
        return HttpResponse("Error al cargar la boleta.")
"""  """
def es_bodeguero(user):
    return Trabajador.objects.filter(usuario=user, cargo='Bodeguero').exists()

@login_required
@user_passes_test(es_bodeguero)
def panel_bodeguero(request):
    productos = Producto.objects.all()
    pedidos = Pedido.objects.all()
    return render(request, 'bodega/panel.html', {'productos': productos, 'pedidos': pedidos})

@login_required
@user_passes_test(es_bodeguero)
def cambiar_estado_pedido(request, id_pedido):
    if request.method == 'POST':
        pedido = get_object_or_404(Pedido, id_pedido=id_pedido)
        nuevo_estado = request.POST.get('nuevo_estado')
        pedido.estado = nuevo_estado
        pedido.save()
    return redirect('panel_bodeguero')
