"""Conservative configured USD estimates; never provider invoices or subscription quota."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import re
from urllib.parse import urlsplit

from .core import Blocked


def decimal_amount(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]{0,8})(\.[0-9]{1,6})?', value):
        raise Blocked('USD amounts/rates must be nonnegative decimal strings with at most six places')
    return Decimal(value)


def micros(value):
    return int(decimal_amount(value) * 1000000)


def dollars(value):
    return format(Decimal(value) / 1000000, '.6f')


def validate_price(price):
    required = {'input_usd_per_million', 'cached_input_usd_per_million', 'output_usd_per_million',
                'basis', 'source', 'valid_until'}
    if not isinstance(price, dict) or set(price) != required or price['basis'] != 'configured_estimate':
        raise Blocked('Price snapshot must explicitly declare configured_estimate and its provenance')
    for key in ('input_usd_per_million', 'cached_input_usd_per_million', 'output_usd_per_million'):
        decimal_amount(price[key])
    try:
        url = urlsplit(price['source'])
        expiry = datetime.fromisoformat(price['valid_until'])
        if (url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment
                or expiry.tzinfo is None): raise ValueError('Invalid provenance')
    except (ValueError, TypeError, AttributeError) as error:
        raise Blocked('Price requires an HTTPS source and timezone-aware validity date') from error
    return price


def price_for(policy, pool, model):
    price = policy.get('prices', {}).get(pool + ':' + model)
    if price is None:
        raise Blocked('Missing configured USD price for ' + pool + ':' + model)
    validate_price(price)
    if datetime.fromisoformat(price['valid_until']) <= datetime.now(timezone.utc):
        raise Blocked('Configured USD price expired; explicit review required')
    return price


def estimate(metrics, price):
    inputs, outputs = metrics['known_input_tokens'], metrics['known_output_tokens']
    cached = metrics.get('cached_input_tokens')
    if type(cached) is not int or not 0 <= cached <= inputs:
        cached = 0  # No unobserved cache discount; conservative estimate.
    value = ((inputs - cached) * decimal_amount(price['input_usd_per_million'])
             + cached * decimal_amount(price['cached_input_usd_per_million'])
             + outputs * decimal_amount(price['output_usd_per_million']))
    # USD per million tokens maps directly to microdollars per token; round up once.
    return int(value.to_integral_value(rounding=ROUND_CEILING))
