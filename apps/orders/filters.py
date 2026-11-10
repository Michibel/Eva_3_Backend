import django_filters
from .models import Order, PaymentStatus

class OrderFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method='filter_status')
    payment_status = django_filters.CharFilter(method='filter_payment_status')

    class Meta:
        model = Order
        fields = ['status', 'client', 'payment_status']

    def filter_status(self, queryset, name, value):
        if not value:
            return queryset
        if ',' in value:
            statuses = [s.strip() for s in value.split(',') if s.strip()]
            return queryset.filter(status__in=statuses)
        return queryset.filter(status=value)

    def filter_payment_status(self, queryset, name, value):
        if not value:
            return queryset
        if value == 'PAGADO_TOTAL':
            return queryset.filter(payments__status=PaymentStatus.PAGADO_TOTAL).distinct()
        elif value == 'PAGADO_PARCIAL':
            return queryset.filter(payments__status=PaymentStatus.PAGADO_PARCIAL).distinct()
        elif value == 'PENDIENTE':
            return queryset.exclude(payments__status__in=[PaymentStatus.PAGADO_TOTAL, PaymentStatus.PAGADO_PARCIAL]).distinct()
        return queryset
