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
    (r'^$', 'pagosonline.views.pay_ship_info', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-step2'),
    (r'^confirm/$', 'pagosonline.views.confirm_info', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-step3'),
    (r'^answer/$', 'pagosonline.views.answerpay', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-answer'),
    (r'^notify/$', 'pagosonline.views.notify_callback', {'SSL': ssl}, 'PAGOSONLINE_satchmo_checkout-notify_callback'),
    (r'^confirmorder/$', 'payment.views.confirm.confirm_free_order', {'SSL' : ssl, 'key' : 'PAGOSONLINE'}, 'PAGOSONLINE_satchmo_checkout_free-confirm')
)
