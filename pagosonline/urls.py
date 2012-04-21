#
#   Pagos Online
#
#   Author: Mauricio Mercado <maumercado (at) gmail.com>
#   with a great help of ingenieroariel
#
#
from django.conf.urls.defaults import patterns
from satchmo_store.shop.satchmo_settings import get_satchmo_setting

ssl = get_satchmo_setting('SSL', default_value=False)

urlpatterns = patterns('',
    (r'^$', 'payment.modules.pagosonline.views.pay_ship_info', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-step2'),
    (r'^confirm/$', 'payment.modules.pagosonline.views.confirm_info', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-step3'),
#    (r'^success/$', 'payment.views.checkout.success', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-success'),
#    (r'^failure/$', 'payment.views.checkout.failure', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-failure'),
    (r'^answer/$', 'payment.modules.pagosonline.views.answerpay', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-answer'),
    (r'^notify/$', 'payment.modules.pagosonline.views.notify_callback', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-notify_callback'),
    (r'^confirmorder/$', 'payment.views.confirm.confirm_free_order', {'SSL' : ssl, 'key' : 'PAGOSONLINE'}, 'PAGOSONLINE_satchmo_checkout_free-confirm')
)
