from django.urls import path
from . import views

urlpatterns = [ 
    path('', views.inicio, name='inicio'),  
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('catalogo/', views.catalogo_view, name='catalogo'),
    path('carrito/agregar', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('generar-factura/', views.generar_factura, name='generar_factura'),
    path('enviar-factura-email/', views.enviar_factura_email, name='enviar_factura_email'),
    path('carrito/actualizar/', views.actualizar_item, name='actualizar_item'),
    path('carrito/eliminar/', views.eliminar_item, name='eliminar_item'),
    path('pago/', views.ir_al_pago, name='ir_al_pago'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('pago/', views.ir_al_pago, name='ir_al_pago'),
    path('procesar-pago/', views.procesar_pago_b2c, name='procesar_pago_b2c'),
    path('api/costo-envio/', views.api_costo_envio, name='api_costo_envio'),
    path('webpay/pagar/', views.iniciar_pago_webpay, name='webpay_pagar'),
    path('webpay/retorno/', views.retorno_pago_webpay, name='webpay_retorno'),
    path('procesar-pago-b2c/', views.procesar_pago_b2c, name='procesar_pago_b2c'),
    path('bodega/', views.panel_bodeguero, name='panel_bodeguero'),
    path('bodega/pedido/<int:id_pedido>/estado/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),

]

