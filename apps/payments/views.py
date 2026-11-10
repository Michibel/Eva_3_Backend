"""
Views para WebPay Transbank
Integración con SDK Transbank (sandbox/producción)
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

from .models import WebPayTransaction
from .serializers import WebPayTransactionSerializer, WebPayInitSerializer, WebPayConfirmSerializer
from apps.orders.models import Order, Payment, PaymentMethod, PaymentStatus


# Importar SDK Transbank (manejar si no está instalado)
try:
    from transbank.webpay.webpay_plus.transaction import Transaction
    from transbank.common.integration_type import IntegrationType
    from transbank.common.options import WebpayOptions
    TRANSBANK_AVAILABLE = True
except ImportError:
    TRANSBANK_AVAILABLE = False
    Transaction = None
    IntegrationType = None
    WebpayOptions = None


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff_member()


class WebPayTransactionViewSet(viewsets.ModelViewSet):
    queryset = WebPayTransaction.objects.select_related('order__client', 'payment').all()
    serializer_class = WebPayTransactionSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'order']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENTE':
            return WebPayTransaction.objects.filter(order__client__user=user).select_related('order', 'payment')
        return WebPayTransaction.objects.select_related('order__client', 'payment').all()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_val = self.kwargs.get(lookup_url_kwarg)
        
        obj = None
        if lookup_val is not None:
            if str(lookup_val).isdigit():
                obj = queryset.filter(pk=lookup_val).first()
            if not obj:
                obj = queryset.filter(token=lookup_val).first()
        
        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound("Transacción WebPay no encontrada.")
            
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, methods=['post'], url_path='init')
    def init_transaction(self, request):
        """
        Iniciar transacción WebPay
        POST /api/v1/webpay-transactions/init/
        Body: {order_id, amount, return_url}
        """
        if not TRANSBANK_AVAILABLE:
            return Response(
                {'detail': 'SDK Transbank no disponible. Instale transbank-sdk.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        serializer = WebPayInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        amount = serializer.validated_data['amount']
        return_url = serializer.validated_data['return_url']

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'detail': 'Pedido no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Generar buy_order único
        import uuid
        buy_order = f"DA-{order.id}-{uuid.uuid4().hex[:8].upper()}"
        session_id = f"sess-{uuid.uuid4().hex[:12]}"

        # Configurar opciones WebPay
        commerce_code = getattr(settings, 'WEBPAY_COMMERCE_CODE', '597055555532')
        api_key = getattr(settings, 'WEBPAY_API_KEY', '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C')
        environment = getattr(settings, 'WEBPAY_ENVIRONMENT', 'INTEGRATION')

        if environment == 'LIVE':
            integration_type = IntegrationType.LIVE
        else:
            integration_type = IntegrationType.TEST

        options = WebpayOptions(commerce_code, api_key, integration_type)

        try:
            tx = Transaction(options)
            response = tx.create(
                buy_order=buy_order,
                session_id=session_id,
                amount=float(amount),
                return_url=return_url,
            )

            # Crear registro de transacción
            webpay_tx = WebPayTransaction.objects.create(
                order=order,
                buy_order=buy_order,
                session_id=session_id,
                amount=amount,
                status='INICIADA',
                token=response.get('token', ''),
                return_url=return_url,
                final_url=return_url,
            )

            return Response({
                'token': response.get('token'),
                'url': response.get('url'),
                'transaction_id': webpay_tx.id,
                'buy_order': buy_order,
            })

        except Exception as e:
            logger.error(f"Error iniciando WebPay: {e}")
            return Response(
                {'detail': f'Error al iniciar transacción: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='confirm')
    def confirm_transaction(self, request):
        """
        Confirmar transacción WebPay (callback desde Transbank)
        POST /api/v1/webpay-transactions/confirm/
        Body: {token_ws}
        """
        if not TRANSBANK_AVAILABLE:
            return Response(
                {'detail': 'SDK Transbank no disponible.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        serializer = WebPayConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token_ws']

        try:
            webpay_tx = WebPayTransaction.objects.get(token=token)
        except WebPayTransaction.DoesNotExist:
            return Response({'detail': 'Transacción no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        # Configurar opciones
        commerce_code = getattr(settings, 'WEBPAY_COMMERCE_CODE', '597055555532')
        api_key = getattr(settings, 'WEBPAY_API_KEY', '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C')
        environment = getattr(settings, 'WEBPAY_ENVIRONMENT', 'INTEGRATION')

        if environment == 'LIVE':
            integration_type = IntegrationType.LIVE
        else:
            integration_type = IntegrationType.TEST

        options = WebpayOptions(commerce_code, api_key, integration_type)

        try:
            tx = Transaction(options)
            response = tx.commit(token=token)

            # Actualizar transacción
            webpay_tx.response_code = response.get('response_code')
            webpay_tx.authorization_code = response.get('authorization_code', '')
            webpay_tx.payment_type_code = response.get('payment_type_code', '')
            webpay_tx.installments_number = response.get('installments_number')
            webpay_tx.response_json = response

            if response.get('response_code') == 0:
                # Transacción autorizada
                webpay_tx.status = 'AUTORIZADA'
                webpay_tx.confirmed_at = timezone.now()

                # Crear/actualizar Payment
                payment, created = Payment.objects.get_or_create(
                    order=webpay_tx.order,
                    amount=webpay_tx.amount,
                    method=PaymentMethod.WEBPAY,
                    defaults={
                        'status': PaymentStatus.PAGADO_TOTAL,
                        'transaction_id': webpay_tx.authorization_code,
                        'paid_at': timezone.now(),
                    }
                )
                if not created:
                    payment.status = PaymentStatus.PAGADO_TOTAL
                    payment.transaction_id = webpay_tx.authorization_code
                    payment.paid_at = timezone.now()
                    payment.save()

                webpay_tx.payment = payment
            else:
                webpay_tx.status = 'RECHAZADA'

            webpay_tx.save()

            return Response({
                'status': webpay_tx.status,
                'response_code': webpay_tx.response_code,
                'authorization_code': webpay_tx.authorization_code,
                'amount': float(webpay_tx.amount),
                'order_id': webpay_tx.order.id,
            })

        except Exception as e:
            logger.error(f"Error confirmando WebPay: {e}")
            webpay_tx.status = 'ERROR'
            webpay_tx.response_json = {'error': str(e)}
            webpay_tx.save()
            return Response(
                {'detail': f'Error al confirmar transacción: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Anular/Reembolsar transacción (solo si está autorizada)"""
        if not TRANSBANK_AVAILABLE:
            return Response({'detail': 'SDK Transbank no disponible.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        webpay_tx = self.get_object()

        if webpay_tx.status != 'AUTORIZADA':
            return Response({'detail': 'Solo se pueden anular transacciones autorizadas.'}, status=status.HTTP_400_BAD_REQUEST)

        amount = request.data.get('amount', float(webpay_tx.amount))

        try:
            commerce_code = getattr(settings, 'WEBPAY_COMMERCE_CODE', '597055555532')
            api_key = getattr(settings, 'WEBPAY_API_KEY', '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C')
            environment = getattr(settings, 'WEBPAY_ENVIRONMENT', 'INTEGRATION')

            if environment == 'LIVE':
                integration_type = IntegrationType.LIVE
            else:
                integration_type = IntegrationType.TEST

            options = WebpayOptions(commerce_code, api_key, integration_type)
            tx = Transaction(options)

            response = tx.refund(
                token=webpay_tx.token,
                amount=amount,
            )

            webpay_tx.status = 'ANULADA'
            webpay_tx.response_json = response
            webpay_tx.save()

            # Actualizar payment
            if webpay_tx.payment:
                webpay_tx.payment.status = PaymentStatus.REEMBOLSADO
                webpay_tx.payment.save()

            return Response({'detail': 'Transacción anulada correctamente.', 'response': response})

        except Exception as e:
            logger.error(f"Error anulando WebPay: {e}")
            return Response({'detail': f'Error al anular: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Cancelar transacción iniciada (solo si está INICIADA o PENDIENTE)"""
        webpay_tx = self.get_object()

        if webpay_tx.status not in ['INICIADA', 'PENDIENTE']:
            return Response({'detail': 'Solo se pueden cancelar transacciones iniciadas o pendientes.'}, status=status.HTTP_400_BAD_REQUEST)

        webpay_tx.status = 'CANCELADA'
        webpay_tx.save()

        return Response({'detail': 'Transacción cancelada correctamente.'})

    @action(detail=False, methods=['post'], url_path='conciliation')
    def conciliation(self, request):
        """
        Conciliar transacciones WebPay por fecha
        POST /api/v1/webpay-transactions/conciliation/
        Body: {date: "YYYY-MM-DD"}
        """
        if not TRANSBANK_AVAILABLE:
            return Response(
                {'detail': 'SDK Transbank no disponible.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        date_str = request.data.get('date')
        if not date_str:
            return Response({'detail': 'Fecha requerida (YYYY-MM-DD).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'detail': 'Formato de fecha inválido. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        # Obtener transacciones del día
        transactions = WebPayTransaction.objects.filter(
            created_at__date=date
        ).select_related('order__client', 'payment')

        results = {
            'date': date_str,
            'total_transactions': transactions.count(),
            'by_status': {},
            'details': [],
            'discrepancies': [],
        }

        for tx in transactions:
            tx_data = {
                'id': tx.id,
                'token': tx.token,
                'buy_order': tx.buy_order,
                'amount': float(tx.amount),
                'status': tx.status,
                'response_code': tx.response_code,
                'authorization_code': tx.authorization_code,
                'order_id': tx.order.id if tx.order else None,
                'client': tx.order.client.name if tx.order and tx.order.client else None,
                'payment_id': tx.payment.id if tx.payment else None,
                'payment_status': tx.payment.status if tx.payment else None,
                'created_at': tx.created_at,
                'confirmed_at': tx.confirmed_at,
            }
            results['details'].append(tx_data)

            # Contar por estado
            results['by_status'][tx.status] = results['by_status'].get(tx.status, 0) + 1

            # Detectar discrepancias
            if tx.status == 'AUTORIZADA' and not tx.payment:
                results['discrepancies'].append({
                    'type': 'missing_payment',
                    'transaction': tx_data,
                    'message': 'Transacción autorizada pero sin Payment asociado'
                })
            elif tx.payment and tx.payment.status != PaymentStatus.PAGADO_TOTAL and tx.status == 'AUTORIZADA':
                results['discrepancies'].append({
                    'type': 'payment_status_mismatch',
                    'transaction': tx_data,
                    'message': f'Payment status es {tx.payment.status} pero WebPay está AUTORIZADA'
                })

        return Response(results)