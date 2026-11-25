"""
Payment Gateway Service Layer for Antique Hub.
Provides a replaceable gateway architecture (Demo Sandbox, with pluggable support for Razorpay / Stripe).
Includes Luhn algorithm checksum verification, card expiry checks, CVV verification,
PCI-DSS compliance (only stores last 4 digits, never full PAN or CVV), and unique transaction ID generation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
import importlib
import re
import time
import uuid
from typing import Optional, Tuple
from django.conf import settings


@dataclass
class PaymentResult:
    """
    Standardized result returned by any payment gateway implementation.
    Strictly adheres to PCI-DSS: NEVER contains full card number or CVV.
    """
    success: bool
    transaction_id: str
    amount: Decimal
    method: str
    card_last4: Optional[str] = None
    card_type: Optional[str] = None
    bank_name: Optional[str] = None
    status: str = 'Success'
    error_message: Optional[str] = None


class BasePaymentGateway(ABC):
    """
    Abstract Base Class for Antique Hub Payment Gateways.
    Allows easy swapping between Demo Sandbox, Razorpay, Stripe, or other gateways.
    """

    @abstractmethod
    def process_card_payment(self, order, card_data: dict) -> PaymentResult:
        """
        Process a Credit or Debit Card payment.
        card_data dict contains:
            - card_holder (str)
            - card_number (str)
            - exp_month (int/str)
            - exp_year (int/str)
            - cvv (str)
            - method (Credit Card / Debit Card)
            - bank_name (str, optional)
        """
        pass

    @abstractmethod
    def process_cod_payment(self, order, cod_data: dict = None) -> PaymentResult:
        """
        Process Cash on Delivery (COD) payment.
        """
        pass

    @abstractmethod
    def refund_payment(self, payment_record) -> PaymentResult:
        """
        Process a simulated refund.
        """
        pass


class DemoPaymentGateway(BasePaymentGateway):
    """
    Simulated Sandbox Payment Gateway for Antique Hub.
    - Full Luhn algorithm (Mod-10) card number validation.
    - Expiration date checking against current month & year.
    - CVV format validation.
    - Card network brand detection (Visa, MasterCard, RuPay, Amex, Discover).
    - Issuing bank resolution.
    - Nonce / Unique Transaction ID generation.
    - Zero PAN/CVV storage (PCI-DSS compliance).
    """

    @staticmethod
    def validate_luhn(card_number: str) -> bool:
        """
        Validates card number using the Luhn algorithm (MOD-10 formula).
        Used by major credit/debit card issuers worldwide.
        """
        cleaned = re.sub(r'[\s-]', '', str(card_number or ''))
        if not cleaned.isdigit() or not (13 <= len(cleaned) <= 19):
            return False

        digits = [int(c) for c in cleaned]
        checksum = 0
        reverse_digits = digits[::-1]

        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = digit * 2
                checksum += (doubled - 9) if doubled > 9 else doubled
            else:
                checksum += digit

        return checksum % 10 == 0

    @staticmethod
    def validate_expiry(exp_month, exp_year) -> Tuple[bool, str]:
        """
        Validates expiration month and year against current calendar time.
        Handles both 2-digit years (e.g. 27 -> 2027) and 4-digit years.
        """
        try:
            m = int(exp_month)
            y = int(exp_year)
        except (ValueError, TypeError):
            return False, "Expiry month and year must be valid numbers."

        if y < 100:
            y += 2000

        if not (1 <= m <= 12):
            return False, "Expiration month must be between 1 and 12."

        now = datetime.now()
        current_year = now.year
        current_month = now.month

        if y < current_year or (y == current_year and m < current_month):
            return False, "The card expiration date cannot be in the past."

        if y > current_year + 30:
            return False, "Expiration year is too far into the future."

        return True, ""

    @staticmethod
    def detect_card_type(card_number: str) -> str:
        """
        Identifies card network / brand based on Bank Identification Number (BIN) prefix.
        Supports Visa, MasterCard, RuPay (India), American Express, and Discover.
        """
        cleaned = re.sub(r'[\s-]', '', str(card_number or ''))
        if not cleaned:
            return "Unknown"

        if cleaned.startswith('4'):
            return 'Visa'
        if len(cleaned) >= 2 and 51 <= int(cleaned[:2]) <= 55:
            return 'MasterCard'
        if len(cleaned) >= 4 and 2221 <= int(cleaned[:4]) <= 2720:
            return 'MasterCard'
        if cleaned.startswith(('60', '65', '81', '82', '508', '353', '356')):
            return 'RuPay'
        if cleaned.startswith(('34', '37')):
            return 'American Express'
        if cleaned.startswith(('6011', '65')) or (len(cleaned) >= 3 and 644 <= int(cleaned[:3]) <= 649):
            return 'Discover'

        return 'RuPay' if len(cleaned) == 16 else 'Visa'

    @staticmethod
    def validate_cvv(cvv: str, card_type: str = 'Visa') -> Tuple[bool, str]:
        """
        Validates CVV/CVC format (3 digits, or 4 for American Express).
        """
        cleaned = str(cvv or '').strip()
        if not cleaned.isdigit():
            return False, "CVV/CVC must contain digits only."

        expected_len = 4 if card_type == 'American Express' else 3
        if len(cleaned) != expected_len:
            return False, f"CVV for {card_type} must be exactly {expected_len} digits."

        return True, ""

    @staticmethod
    def generate_transaction_id(prefix: str = "TXN-AH") -> str:
        """
        Generates a unique, verifiable transaction ID for Antique Hub.
        e.g. TXN-AH-20261020-F8C91A23
        """
        date_str = datetime.now().strftime("%Y%m%d")
        unique_hex = uuid.uuid4().hex[:8].upper()
        return f"{prefix}-{date_str}-{unique_hex}"

    def process_card_payment(self, order, card_data: dict) -> PaymentResult:
        """
        Validates card input using Luhn check and date verification,
        then produces a sanitized PaymentResult with ONLY non-sensitive metadata.
        """
        card_holder = str(card_data.get('card_holder') or '').strip()
        card_number = str(card_data.get('card_number') or '').strip()
        exp_month = card_data.get('exp_month')
        exp_year = card_data.get('exp_year')
        cvv = str(card_data.get('cvv') or '').strip()
        method = card_data.get('method') or 'Credit Card'
        bank_name = str(card_data.get('bank_name') or '').strip()

        # 1. Card Holder Name check
        if not card_holder or len(card_holder) < 3:
            return PaymentResult(
                success=False,
                transaction_id="",
                amount=order.tot_amt,
                method=method,
                error_message="Cardholder name is required (minimum 3 characters)."
            )

        # 2. Luhn Algorithm Validation
        cleaned_number = re.sub(r'[\s-]', '', card_number)
        if not self.validate_luhn(cleaned_number):
            return PaymentResult(
                success=False,
                transaction_id="",
                amount=order.tot_amt,
                method=method,
                error_message="Invalid card number: failed Luhn algorithm checksum verification."
            )

        # 3. Detect Card Network
        card_type = self.detect_card_type(cleaned_number)

        # 4. Expiry Date Validation
        valid_exp, exp_err = self.validate_expiry(exp_month, exp_year)
        if not valid_exp:
            return PaymentResult(
                success=False,
                transaction_id="",
                amount=order.tot_amt,
                method=method,
                error_message=exp_err
            )

        # 5. CVV Check
        valid_cvv, cvv_err = self.validate_cvv(cvv, card_type)
        if not valid_cvv:
            return PaymentResult(
                success=False,
                transaction_id="",
                amount=order.tot_amt,
                method=method,
                error_message=cvv_err
            )

        # 6. Resolve issuing bank name fallback if empty
        if not bank_name:
            if card_type == 'RuPay':
                bank_name = 'State Bank of India'
            elif card_type == 'Visa':
                bank_name = 'HDFC Bank'
            elif card_type == 'MasterCard':
                bank_name = 'ICICI Bank'
            else:
                bank_name = 'Axis Bank'

        # 7. Generate Transaction Reference
        txn_id = self.generate_transaction_id("TXN-AH")
        last4 = cleaned_number[-4:]

        # SUCCESS: Returns ONLY last 4 digits, card type, bank name, amount, date & transaction ID.
        # Zero full card number or CVV is returned or stored!
        return PaymentResult(
            success=True,
            transaction_id=txn_id,
            amount=order.tot_amt,
            method=method,
            card_last4=last4,
            card_type=card_type,
            bank_name=bank_name,
            status='Success'
        )

    def process_cod_payment(self, order, cod_data: dict = None) -> PaymentResult:
        """
        Processes Cash on Delivery (COD) payment authorization.
        """
        txn_id = self.generate_transaction_id("COD-AH")
        return PaymentResult(
            success=True,
            transaction_id=txn_id,
            amount=order.tot_amt,
            method='Cash on Delivery',
            card_last4=None,
            card_type=None,
            bank_name='Cash on Delivery (Courier Settlement)',
            status='Success'
        )

    def refund_payment(self, payment_record) -> PaymentResult:
        """
        Simulates an automated refund back to the buyer's payment instrument.
        """
        refund_txn = self.generate_transaction_id("REF-AH")
        return PaymentResult(
            success=True,
            transaction_id=refund_txn,
            amount=payment_record.amount,
            method=payment_record.method,
            card_last4=payment_record.card_last4,
            card_type=payment_record.card_type,
            bank_name=payment_record.bank_name,
            status='Refunded'
        )


class RazorpayTestGateway(BasePaymentGateway):
    """
    Pluggable Razorpay Test Mode Gateway placeholder.
    Demonstrates how Razorpay test mode can be hooked into Antique Hub
    without changing any views or controller code.
    """

    def __init__(self, key_id: str = None, key_secret: str = None):
        self.key_id = key_id or getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_demo')
        self.key_secret = key_secret or getattr(settings, 'RAZORPAY_KEY_SECRET', 'test_secret')

    def process_card_payment(self, order, card_data: dict) -> PaymentResult:
        # In actual Razorpay integration, this would verify razorpay_signature or create an Order API call
        demo_gateway = DemoPaymentGateway()
        res = demo_gateway.process_card_payment(order, card_data)
        if res.success:
            res.transaction_id = f"pay_rzp_{uuid.uuid4().hex[:14]}"
        return res

    def process_cod_payment(self, order, cod_data: dict = None) -> PaymentResult:
        demo_gateway = DemoPaymentGateway()
        return demo_gateway.process_cod_payment(order, cod_data)

    def refund_payment(self, payment_record) -> PaymentResult:
        return PaymentResult(
            success=True,
            transaction_id=f"rfnd_rzp_{uuid.uuid4().hex[:14]}",
            amount=payment_record.amount,
            method=payment_record.method,
            status='Refunded'
        )


def get_payment_gateway() -> BasePaymentGateway:
    """
    Factory function resolving the active payment gateway service class from settings.
    Defaults to DemoPaymentGateway for sandbox demonstration.
    Configurable via settings.PAYMENT_GATEWAY_CLASS = 'payments.services.RazorpayTestGateway'
    """
    gateway_class_path = getattr(settings, 'PAYMENT_GATEWAY_CLASS', 'payments.services.DemoPaymentGateway')
    try:
        module_name, class_name = gateway_class_path.rsplit('.', 1)
        mod = importlib.import_module(module_name)
        gateway_cls = getattr(mod, class_name)
        return gateway_cls()
    except Exception:
        return DemoPaymentGateway()
