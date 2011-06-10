#
#
#   Author: Mauricio Mercado <maumercado (at) gmail.com>
#   with a great help of ingenieroariel
#
#   Based on "Manual de Integracion Tradicional Pagos Online" ver. 3.1, 2009, PAGOSONLINE
#   For more information about integration look at http://ayuda.pagosonline.com/
#
#

from datetime import datetime
from decimal import Decimal
from django.core import urlresolvers
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from livesettings import config_get_group, config_value
from payment.utils import get_processor_by_key
from payment.views import payship
from satchmo_store.contact.models import Contact
from satchmo_store.shop.models import Order, Cart
from satchmo_store.shop.satchmo_settings import get_satchmo_setting
from satchmo_utils.dynamic import lookup_url, lookup_template
from satchmo_utils.views import bad_or_missing
import logging
from django.views.decorators.csrf import csrf_exempt


try:
    from hashlib import md5
except ImportError:
    # python < 2.5
    from md5 import md5
log = logging.getLogger()

def pay_ship_info(request):
    return payship.base_pay_ship_info(
            request,
            config_get_group('PAYMENT_PAGOSONLINE'), payship.simple_pay_ship_process_form,
            'shop/checkout/pagosonline/pay_ship.html'
            )
pay_ship_info = never_cache(pay_ship_info)


def _resolve_local_url(payment_module, cfgval, ssl=False):
    try:
        return lookup_url(payment_module, cfgval.value, include_server=True, ssl=ssl)
    except urlresolvers.NoReverseMatch:
        return cfgval.value


def confirm_info(request):
    payment_module = config_get_group('PAYMENT_PAGOSONLINE')

    try:
        order = Order.objects.from_request(request)
        get_buyer_email = Contact.objects.filter(id=order.contact_id)
    except Order.DoesNotExist:
        url = lookup_url(payment_module, 'satchmo_checkout-step1')
        return HttpResponseRedirect(url)

    tempCart = Cart.objects.from_request(request)
    if tempCart.numItems == 0:
        template = lookup_template(payment_module, 'shop/checkout/empty_cart.html')
        return render_to_response(template,
                                  context_instance=RequestContext(request))

    # Check if the order is still valid
    if not order.validate(request):
        context = RequestContext(request, {'message': _('Your order is no longer valid.')})
        return render_to_response('shop/404.html', context_instance=context)

    # Check if we are in test or real mode
    live = payment_module.LIVE.value
    if live:
        post_url = payment_module.POST_URL.value
        prueba = 0
    else:
        post_url = payment_module.POST_TEST_URL.value
        prueba = 1
    #
    # PAGOSONLINE system does not accept multiple payment attempts with the same refVenta, even
    # if the previous one has never been finished. The worse is that it does not display
    # any message which could be understood by an end user.
    #
    # If user goes to PAGOSONLINE page and clicks 'back' button (e.g. to correct contact data),
    # the next payment attempt will be rejected.
    #
    # To provide higher probability of refVenta uniqueness, we add YYYY:DD:MM:hh:mm:ss timestamp part
    # to the order id, separated by 'T' character in the following way:
    #
    #   refVenta: xxxxxxxTYYYYDDMMHHMMSS
    #
    now = datetime.now()
    xchg_order_id = "%dT%04d%02d%02d%02d%02d%02d" % (order.id, now.year, now.day, now.month, now.hour, now.minute, now.second)

    signature_code = payment_module.MERCHANT_SIGNATURE_CODE.value
    userId = payment_module.MERCHANT_USERID_CODE.value
    amount = "%.2f" % order.balance
    log.debug("Amount for confirm Info %s" % amount)
    coin = payment_module.MERCHANT_CURRENCY.value
    signature_data = '~'.join(
            map(str, (
                    signature_code,
                    userId,
                    xchg_order_id,
                    amount,
                    coin,
                    )))

    try:
        cartnumber = request.session['cart']
    except KeyError:
        log.debug("No cart number found %s", request.session)
    
    signature=md5(signature_data).hexdigest()
    template = lookup_template(payment_module, 'shop/checkout/pagosonline/confirm.html')

    url_callback = _resolve_local_url(payment_module, payment_module.MERCHANT_URL_CALLBACK, ssl=get_satchmo_setting('SSL'))
    url_ans = _resolve_local_url(payment_module, payment_module.MERCHANT_URL_OK)
#    url_ko = _resolve_local_url(payment_module, payment_module.MERCHANT_URL_KO)
    
    try:
        request.user.email
        emailComprador = request.user.email
    except:
        emailComprador = get_buyer_email[0].email

    float_balance = float(order.balance)
    no_iva = float_balance/1.16
    iva = round(0.16*no_iva,2)
    
    log.debug("IVA = %f" % iva)

    ctx = {
        'live': live,
        'post_url': post_url,
        'coin': payment_module.MERCHANT_CURRENCY.value,
        'url_callback': url_callback,
        'url_ans': url_ans,
        'usuarioId': userId,
	    'order': order,
        'xchg_order_id': xchg_order_id,
        'amount': amount,
        'iva': iva,
        'signature': signature,
	    'prueba': prueba,
        'emailComprador': emailComprador,
        'default_view_tax': config_value('TAX', 'DEFAULT_VIEW_TAX'),
    }

    log.debug(ctx)

    return render_to_response(template, ctx, context_instance=RequestContext(request))
confirm_info = never_cache(confirm_info)

def answerpay(request):

    payment_module = config_get_group('PAYMENT_PAGOSONLINE')

    try:
        order = Order.objects.from_request(request)
    except Order.DoesNotExist:
        url = lookup_url(payment_module, 'satchmo_checkout-step1')
        return HttpResponseRedirect(url)

    """
    This can be used to generate a receipt or some other confirmation
    """
    data = request.GET
    global estado
    global codigo

    estado = {
	'1': "Sin Abrir",
	'2': "Abierta",
	'4': "Pagada y Abonada",
	'5': "Cancelada",
	'6': "Rechazada",
	'7': "Validacion",
	'8': "Reversada",
	'9': "Reversada fraudulenta",
	'10': "Enviada a ente financiero",
	'11': "Capturando datos tarjeta de credito",
	'12': "Esperando confirmacion sistema PSE",
	'13': "Activa Debitos ACH",
	'14': "Confirmando pago Efecty",
	'15': "Impreso",
	'16': "Debito ACH Registrado",
	}

    codigo = {
	'1': "Transaccion aprobada",
	'2': "Pago cancelado por el usuario",
	'3': "Pago cancelado por el usuario durante validacion",
	'4': "Transaccion rechazada por la entidad",
	'5': "Transaccion declinada por la entidad",
	'6': "Fondos insuficientes",
	'7': "Tarjeta invalida",
	'8': "Acuda a su entidad",
	'9': "Tarjeta vencida",
	'10': "Tarjeta restringida",
	'11': "Discrecional POL",
	'12': "Fecha de expiracion o campo seg. Invalidos",
	'13': "Repita transaccion",
	'14': "Transaccion invalida",
	'15': "Transaccion en proceso de validacion",
	'16': "Combinacion usuario-contrasena invalidos",
	'17': "Monto excede maximo permitido por entidad",
	'18': "Documento de identificacion invalido",
	'19': "Transaccion abandonada capturando datos TC",
	'20': "Transaccion abandonada",
	'21': "Imposible reversar transaccion",
	'22': "Tarjeta no autorizada para realizar compras por internet.",
	'23': "Transaccion rechazada",
	'24': "Transaccion parcial aprobada",
	'25': "Rechazada por no confirmacion",
	'26': "Comprobante generado, esperando pago en banco",
	'9994': "Transaccion pendiente por confirmar",
	'9995': "Certificado digital no encontrado",
	'9996': "Entidad no responde",
	'9997': "Error de mensajeria con la entidad financiera",
	'9998': "Error en la entidad financiera",
	'9999': "Error no especificado",
	}

    tipo_pago = {
	'10': "VISA",
	'11': "MASTERCARD",
	'12': "AMEX",
	'22': "DINERS",
	'24': "Verified by VISA",
	'25': "PSE",
	'27': "VISA Debito",
	'30': "Efecty",
	'31': "Pago referenciado",
	}	
    
    try:    
        buyinfo = {
            'coin': payment_module.MERCHANT_CURRENCY.value,
            'ref_venta': data['ref_venta'],
            'order_idpagos': data['ref_pol'],
            'amount': data['valor'],
            'ivatra': data['iva'],
    	    'estadopol': estado[data['estado_pol']],
    	    'codigoresp': codigo[data['codigo_respuesta_pol']],
    	    'fechaprocesamiento': data['fecha_procesamiento'],
    	    'msg': data['mensaje'],
    	    'tipo_medio_pago': tipo_pago[data['medio_pago']],
    	    'emailComprador': data['emailComprador'],
    	    'order': order,
    	}   
    except KeyError:
        return HttpResponseRedirect('/') 
        
    try:
        cartnumber = request.session['cart']
        for cart in Cart.objects.filter(id=cartnumber):
            cart.empty()
    except KeyError:
        pass

    return render_to_response('shop/checkout/pagosonline/answer.html',
                              context_instance=RequestContext(request, buyinfo))

answerpay = never_cache(answerpay)

@csrf_exempt
def notify_callback(request):
    
    payment_module = config_get_group('PAYMENT_PAGOSONLINE')
    signature_code = payment_module.MERCHANT_SIGNATURE_CODE.value
    if payment_module.LIVE.value:
        log.debug("Live on %s", payment_module.KEY.value)
    else:
        log.debug("Test on %s", payment_module.KEY.value)
    data = request.POST

    try:
        sig_data = '~'.join(
            map(str,(signature_code,
                data['usuario_id'],
                data['ref_venta'],
                data['valor'],
                data['moneda'],
                data['estado_pol']
        )))
    
        sig_calc = md5(sig_data).hexdigest()
        if sig_calc != data['firma'].lower():
            log.error("Invalid signature. Received '%s', calculated '%s'. sig_data %s" % (data['firma'], sig_calc, sig_data))
            return HttpResponseBadRequest("Checksum error")

        xchg_order_id = data['ref_venta']
        try:
            order_id = xchg_order_id[:xchg_order_id.index('T')]
            log.debug("Order ID = %s" % order_id)
        except ValueError:
            log.error("Incompatible order ID: '%s'" % xchg_order_id)
            return HttpResponseNotFound("Order not found")
        try:
            order = Order.objects.get(id=order_id)
            log.debug("Order object status = %s" % order.id )
        except Order.DoesNotExist:
            log.error("Received data for nonexistent Order #%s" % order_id)
            return HttpResponseNotFound("Order not found")
        amount = data['valor']
        log.debug("Amount Received in POST %s" % amount)
        trans_id = codigo[data['codigo_respuesta_pol']]
    except KeyError:
        log.error("Received incomplete PAGOSONLINE transaction data")
        return HttpResponseBadRequest("Incomplete data")
    
    # success
    if int(data['codigo_respuesta_pol']) == 1:
        order.add_status(status='New') 
        processor = get_processor_by_key('PAYMENT_PAGOSONLINE')
        payment = processor.record_payment(
            order=order,
            amount=amount,
            transaction_id=trans_id)

    elif int(data['codigo_respuesta_pol']) == 15:
        order.add_status(status='In Process', notes=u"%s " % codigo[data['codigo_respuesta_pol']])
        processor = get_processor_by_key('PAYMENT_PAGOSONLINE')
        payment = processor.record_payment(
            order=order,
            amount=amount,
            transaction_id=trans_id)

    elif int(data['codigo_respuesta_pol']) == 26:
        order.add_status(status='In Process', notes=u"%s " % codigo[data['codigo_respuesta_pol']])
        processor = get_processor_by_key('PAYMENT_PAGOSONLINE')
        payment = processor.record_payment(
            order=order,
            amount=amount,
            transaction_id=trans_id)

    elif int(data['codigo_respuesta_pol']) == 24:
        order.add_status(status='Billed', notes=u"%s" % codigo[data['codigo_respuesta_pol']])
        processor = get_processor_by_key('PAYMENT_PAGOSONLINE')
        payment = processor.record_payment(
            order=order,
            amount=amount,
            transaction_id=trans_id)            

    elif int(data['codigo_respuesta_pol']) == 9994:        
        processor = get_processor_by_key('PAYMENT_PAGOSONLINE')
        payment = processor.record_payment(
            order=order,
            amount=amount,
            transaction_id=trans_id)

    else:
        order.add_status(status='Cancelled', notes=u"%s" % trans_id)

    return HttpResponse()
