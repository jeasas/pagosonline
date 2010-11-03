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
from satchmo_store.shop.models import Order, Cart
from satchmo_store.shop.satchmo_settings import get_satchmo_setting
from satchmo_utils.dynamic import lookup_url, lookup_template
import logging
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
        #terminal = payment_module.MERCHANT_TERMINAL.value
    else:
        post_url = payment_module.POST_TEST_URL.value
        #terminal = payment_module.MERCHANT_TEST_TERMINAL.value
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
    xchg_order_id = "%07dT%04d%02d%02d%02d%02d%02d" % (order.id, now.year, now.day, now.month, now.hour, now.minute, now.second)

    signature_code = payment_module.MERCHANT_SIGNATURE_CODE.value
    userId = payment_module.MERCHANT_USERID_CODE.value
    amount = "%d" % (order.balance)
    signature_data = ''.join(
            map(str, (
                    signature_code,
                    userId,
                    xchg_order_id,
                    amount,
                    payment_module.MERCHANT_CURRENCY.value,
                    )
               )
            )

    signature= md5(signature_data).hexdigest()

    template = lookup_template(payment_module, 'shop/checkout/pagosonline/confirm.html')

    url_callback = _resolve_local_url(payment_module, payment_module.MERCHANT_URL_CALLBACK, ssl=get_satchmo_setting('SSL'))
    url_ok = _resolve_local_url(payment_module, payment_module.MERCHANT_URL_OK)
    url_ko = _resolve_local_url(payment_module, payment_module.MERCHANT_URL_KO)

    ctx = {
        'prueba': live,
        'post_url': post_url,
        'moneda': payment_module.MERCHANT_CURRENCY.value,
        #'MERCHANT_TITULAR': payment_module.MERCHANT_TITULAR.value,
        #'url_callback': url_callback,
        #'url_ok': url_ok,
        #'url_ko': url_ko,
        'descripcion': order,
        'refVenta': xchg_order_id,
        'valor': amount,
        'llave_encripcion': signature,
        'iva': config_value('TAX', 'DEFAULT_VIEW_TAX'),
	'baseDevolucionIva': amount,
    }
    return render_to_response(template, ctx, context_instance=RequestContext(request))
confirm_info = never_cache(confirm_info)

def notify_callback(request):
    payment_module = config_get_group('PAYMENT_PAGOSONLINE')
    signature_code = payment_module.MERCHANT_SIGNATURE_CODE.value
    if payment_module.LIVE.value:
        log.debug("Live IPN on %s", payment_module.KEY.value)
        #terminal = payment_module.MERCHANT_TERMINAL.value
    else:
        log.debug("Test IPN on %s", payment_module.KEY.value)
        #terminal = payment_module.MERCHANT_TEST_TERMINAL.value
    data = request.POST
    log.debug("Transaction data: " + repr(data))
    try:
        sig_data = "%s%s%s%s%s%s" % (
                data['Ds_Amount'],
                data['Ds_Order'],
                data['Ds_MerchantCode'],
                data['Ds_Currency'],
                data['Ds_Response'],
                signature_code
                )
        sig_calc = md5(sig_data).hexdigest()
        if sig_calc != data['Ds_Signature'].lower():
            log.error("Invalid signature. Received '%s', calculated '%s'." % (data['Ds_Signature'], sig_calc))
            return HttpResponseBadRequest("Checksum error")
#        if data['Ds_MerchantCode'] != payment_module.MERCHANT_FUC.value:
#            log.error("Invalid FUC code: %s" % data['Ds_MerchantCode'])
#            return HttpResponseNotFound("Unknown FUC code")
#        if int(data['Ds_Terminal']) != int(terminal):
#            log.error("Invalid terminal number: %s" % data['Ds_Terminal'])
#            return HttpResponseNotFound("Unknown terminal number")
        # TODO: fields Ds_Currency, Ds_SecurePayment may be worth checking

        xchg_order_id = data['Ds_Order']
        try:
            order_id = xchg_order_id[:xchg_order_id.index('T')]
        except ValueError:
            log.error("Incompatible order ID: '%s'" % xchg_order_id)
            return HttpResponseNotFound("Order not found")
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            log.error("Received data for nonexistent Order #%s" % order_id)
            return HttpResponseNotFound("Order not found")
        amount = Decimal(data['Ds_Amount']) / Decimal('100')    # is in cents, divide it
        if int(data['Ds_Response']) > 100:
            log.info("Response code is %s. Payment not accepted." % data['Ds_Response'])
            return HttpResponse()
    except KeyError:
        log.error("Received incomplete PAGOSONLINE transaction data")
        return HttpResponseBadRequest("Incomplete data")
    # success
    order.add_status(status='New', notes=u"Paid through PAGOSONLINE.")
    processor = get_processor_by_key('PAYMENT_PAGOSONLINE')
    payment = processor.record_payment(
        order=order,
        amount=amount)
        #transaction_id=data['Ds_AuthorisationCode'])
    # empty customer's carts
    for cart in Cart.objects.filter(customer=order.contact):
        cart.empty()
    return HttpResponse()
   
