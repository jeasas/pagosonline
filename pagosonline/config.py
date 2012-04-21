#
#
#   Author: Mauricio Mercado <maumercado (at) gmail.com>
#   with a great help of ingenieroariel
#
#   Based on "Manual de Integracion Tradicional Pagos Online" ver. 3.1, 2009, PAGOSONLINE
#   For more information about integration look at http://ayuda.pagosonline.com/
#
# 
from livesettings import *
from django.utils.translation import ugettext_lazy as _

PAYMENT_GROUP = ConfigurationGroup('PAYMENT_PAGOSONLINE',
    _('PAGOSONLINE Payment Module Settings'))

config_register_list(
    ModuleValue(PAYMENT_GROUP,
        'MODULE',
        description=_('Implementation module'),
        hidden=True,
        default = 'payment.modules.pagosonline',
        ),
    StringValue(PAYMENT_GROUP,
        'KEY',
        description=_("Module key"),
        hidden=True,
        default = 'PAGOSONLINE',
        ),
    StringValue(PAYMENT_GROUP,
    	'LABEL',
    	description=_('English name for this group on the checkout screens'),
    	default = 'Pagos Online',
    	help_text = _('This will be passed to the translation utility'),
	),
    StringValue(PAYMENT_GROUP,
        'URL_BASE',
        description=_('The url base used for constructing urlpatterns which will use this module'),
        default = '^pagosonline/',
        ordering=20,
        ),
    BooleanValue(
        PAYMENT_GROUP,
        'LIVE',
        description=_("Accept real payments"),
        help_text=_("False if you want to be in test mode"),
        default=False,
        ordering=30,
        ),
    StringValue(
        PAYMENT_GROUP,
        'MERCHANT_CURRENCY',
        description=_('Currency'),
        default='COP',
        choices=[
            ('EUR', _("Euros")),
            ('COP', _("Colombian Pesos")),
            ('GBP', _("British Pound")),
            ('MXN', _("Mexican Pesos")),
            ('USD', _("U.S. Dollar")),
            ('VEB', _("Strong Bolivar")),
            ],
        ordering=40,
        ),
    StringValue(
        PAYMENT_GROUP,
        'MERCHANT_TITULAR',
        description=_('Merchant title'),
        help_text=_('Description of your shop which will be visible on payment confirmation screen'),
        ordering=60,
        ),

    # signature
    StringValue(
        PAYMENT_GROUP,
        'MERCHANT_SIGNATURE_CODE',
        description=_('Signature code'),
        help_text=_('Your secret code used to sign transaction data'),
        ordering=100,
        ),
    StringValue(
        PAYMENT_GROUP,
        'MERCHANT_USERID_CODE',
        description=_('User ID'),
        help_text=_('Your userid provided by PAGOSONLINE'),
        ordering=200,
        ),

    # post url
    StringValue(
        PAYMENT_GROUP,
        'POST_URL',
        description=_('Post URL'),
        help_text=_('The PAGOSONLINE URL for transaction posting.'),
        default="https://gateway.pagosonline.net/apps/gateway/index.html",
        ordering=120,
        ),
    StringValue(
        PAYMENT_GROUP,
        'POST_TEST_URL',
        description=_('Post URL Test'),
        help_text=_('The PAGOSONLINE URL for transaction posting.'),
        default="https://gateway2.pagosonline.net/apps/gateway/index.html",
        ordering=120,
        ),
    StringValue(
        PAYMENT_GROUP,
        'MERCHANT_URL_CALLBACK',
        description=_('Callback URL'),
        help_text=_('Callback URL for on-line notifications about payment progress'),
        default='PAGOSONLINE_satchmo_checkout-notify_callback',
        ordering=300,
        ),
    StringValue(
        PAYMENT_GROUP,
        'MERCHANT_URL_OK',
        description=_('OK URL'),
        help_text=_('URL for customer to return after successful payment'),
        default='PAGOSONLINE_satchmo_checkout-answer',
        ordering=310,
        ),
#    StringValue(
#        PAYMENT_GROUP,
#        'MERCHANT_URL_KO',
#        description=_('Failure URL'),
#        help_text=_('URL for customer to return after payment failure'),
#        default='PAGOSONLINE_satchmo_checkout-failure',
#        ordering=320,
#        ),
    BooleanValue(PAYMENT_GROUP,
        'EXTRA_LOGGING',
        description=_("Verbose logs"),
        help_text=_("Add extensive logs during post."),
        default=False,
	)
)
