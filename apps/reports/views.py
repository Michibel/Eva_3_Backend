"""
Views para reportes, dashboards y exportaciones
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
import json

from .models import Report, DashboardWidget
from .serializers import ReportSerializer, DashboardWidgetSerializer, ReportGenerateSerializer
from apps.orders.models import Order, OrderItem, Payment, PaymentStatus, OrderStatus
from apps.production.models import ProductionCard, KanbanColumn
from apps.ingredients.models import Ingredient
from apps.products.models import Product
from apps.clients.models import Client
from apps.dispatch.models import Dispatch, Route


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff_member()


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['widget_type', 'is_active']


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('generated_by').all()
    serializer_class = ReportSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'format']

    def perform_content_negotiation(self, request, force=False):
        format_param = request.query_params.get('format')
        if format_param and format_param.lower() in ['csv', 'excel', 'pdf', 'xlsx']:
            from rest_framework.renderers import BaseRenderer
            class PassthroughRenderer(BaseRenderer):
                media_type = '*/*'
                format = format_param
                def render(self, data, accepted_media_type=None, renderer_context=None):
                    return data
            return (PassthroughRenderer(), '*/*')
        return super().perform_content_negotiation(request, force=force)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generar reporte
        POST /api/v1/reports/generate/
        Body: {report_type, format, filters}
        """
        serializer = ReportGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report_type = serializer.validated_data['report_type']
        format = serializer.validated_data['format']
        filters = serializer.validated_data.get('filters', {})

        # Generar datos según tipo
        data = self._get_report_data(report_type, filters)

        # Crear reporte
        report = Report.objects.create(
            name=f"{report_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            report_type=report_type,
            format=format,
            filters=filters,
            generated_by=request.user,
        )

        # TODO: Generar archivo Excel/PDF según formato
        # Por ahora devolvemos JSON

        return Response({
            'report_id': report.id,
            'data': data,
        })

    @action(detail=False, methods=['get'], url_path=r'(?P<report_type>[^/.]+)/export')
    def export_report(self, request, report_type=None):
        """Exportar reporte en formato Excel, PDF o CSV"""
        report_type = report_type or self.kwargs.get('report_type')
        type_mapping = {
            'sales': 'VENTAS',
            'products': 'RENTABILIDAD',
            'production': 'PRODUCCION',
            'stock': 'STOCK',
            'profitability': 'RENTABILIDAD',
            'clients': 'CLIENTES',
            'dispatch': 'DESPACHOS',
            'payments': 'VENTAS',
        }
        internal_type = type_mapping.get(report_type, 'VENTAS')
        period = request.query_params.get('period', 'month')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        export_format = request.query_params.get('format', 'excel').lower()

        today = timezone.now().date()
        if period == 'today':
            date_from = today
            date_to = today
        elif period == 'week':
            date_from = today - timedelta(days=7)
            date_to = today
        elif period == 'month':
            date_from = today.replace(day=1)
            date_to = today
        elif period == 'quarter':
            quarter_start_month = ((today.month - 1) // 3) * 3 + 1
            date_from = today.replace(month=quarter_start_month, day=1)
            date_to = today
        elif period == 'year':
            date_from = today.replace(month=1, day=1)
            date_to = today

        filters = {}
        if date_from:
            filters['date_from'] = str(date_from)
        if date_to:
            filters['date_to'] = str(date_to)

        data = self._get_report_data(internal_type, filters)
        filename = f"reporte_{report_type}_{today.strftime('%Y%m%d')}"

        if export_format == 'csv':
            import csv
            import io
            from django.http import HttpResponse
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Reporte', internal_type, 'Generado', today.strftime('%Y-%m-%d')])
            writer.writerow([])
            for key, val in data.items():
                if isinstance(val, dict):
                    writer.writerow([key.upper()])
                    for k, v in val.items():
                        writer.writerow([k, v])
                    writer.writerow([])
                elif isinstance(val, list) and val:
                    writer.writerow([key.upper()])
                    headers = list(val[0].keys())
                    writer.writerow(headers)
                    for item in val:
                        writer.writerow([item.get(h, '') for h in headers])
                    writer.writerow([])
            response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            return response

        elif export_format == 'pdf':
            import io
            from django.http import HttpResponse
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            p.drawString(100, 750, f"Dulce Arte - Reporte: {internal_type}")
            p.drawString(100, 730, f"Fecha: {today.strftime('%Y-%m-%d')} | Periodo: {period}")
            y = 700
            for k, val in data.items():
                if y < 100:
                    p.showPage()
                    y = 750
                p.drawString(100, y, f"{k}: {str(val)[:80]}")
                y -= 20
            p.showPage()
            p.save()
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
            return response

        else:
            import io
            import openpyxl
            from django.http import HttpResponse
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = internal_type[:30]
            ws.append(['DULCE ARTE - REPORTE DE ' + internal_type])
            ws.append(['Generado:', today.strftime('%Y-%m-%d'), 'Periodo:', period])
            ws.append([])

            for key, val in data.items():
                if isinstance(val, dict):
                    ws.append([key.upper()])
                    for k, v in val.items():
                        ws.append([k, v])
                    ws.append([])
                elif isinstance(val, list) and val:
                    ws.append([key.upper()])
                    headers = list(val[0].keys())
                    ws.append(headers)
                    for item in val:
                        ws.append([str(item.get(h, '')) for h in headers])
                    ws.append([])

            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            return response

    @action(detail=False, methods=['get'], url_path='(?P<report_type>[^/.]+)')
    def by_type(self, request, report_type=None):
        """
        Obtener datos de reporte por tipo
        GET /api/v1/reports/sales/?period=month
        GET /api/v1/reports/stock/
        etc.
        """
        # Mapear tipos del frontend a tipos internos
        type_mapping = {
            'sales': 'VENTAS',
            'products': 'RENTABILIDAD',  # productos más vendidos = rentabilidad
            'production': 'PRODUCCION',
            'stock': 'STOCK',
            'profitability': 'RENTABILIDAD',
            'clients': 'CLIENTES',
            'dispatch': 'DESPACHOS',
            'payments': 'PAGOS',  # no implementado aún, usar VENTAS
        }

        internal_type = type_mapping.get(report_type, 'VENTAS')
        period = request.query_params.get('period', 'month')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        # Convertir período a fechas
        from datetime import timedelta
        today = timezone.now().date()
        if period == 'today':
            date_from = today
            date_to = today
        elif period == 'week':
            date_from = today - timedelta(days=7)
            date_to = today
        elif period == 'month':
            date_from = today.replace(day=1)
            date_to = today
        elif period == 'quarter':
            quarter_start_month = ((today.month - 1) // 3) * 3 + 1
            date_from = today.replace(month=quarter_start_month, day=1)
            date_to = today
        elif period == 'year':
            date_from = today.replace(month=1, day=1)
            date_to = today

        filters = {}
        if date_from:
            filters['date_from'] = date_from.isoformat()
        if date_to:
            filters['date_to'] = date_to.isoformat()

        data = self._get_report_data(internal_type, filters)

        # Agregar chart_data para el frontend
        chart_data = self._get_chart_data(internal_type, data)
        if chart_data:
            data['chart_data'] = chart_data

        return Response(data)

    def _get_chart_data(self, report_type, data):
        """Generar datos para gráficos"""
        if report_type == 'VENTAS' and 'by_day' in data:
            return {
                'type': 'line',
                'labels': [d['date'] for d in data['by_day']],
                'datasets': [{
                    'label': 'Ventas Diarias',
                    'data': [float(d['total'] or 0) for d in data['by_day']],
                }]
            }
        elif report_type == 'PRODUCCION' and 'by_column' in data:
            return {
                'type': 'bar',
                'labels': [d['column__name'] for d in data['by_column']],
                'datasets': [{
                    'label': 'Tarjetas por Estado',
                    'data': [d['count'] for d in data['by_column']],
                }]
            }
        elif report_type == 'STOCK':
            low_stock = data.get('low_stock', [])
            if low_stock:
                return {
                    'type': 'bar',
                    'labels': [d['name'] for d in low_stock[:10]],
                    'datasets': [{
                        'label': 'Stock Actual',
                        'data': [float(d['current_stock']) for d in low_stock[:10]],
                    }, {
                        'label': 'Stock Mínimo',
                        'data': [float(d['min_stock']) for d in low_stock[:10]],
                    }]
                }
        elif report_type == 'RENTABILIDAD' and 'by_product' in data:
            products = data['by_product'][:10]
            return {
                'type': 'bar',
                'labels': [p['product_name'] for p in products],
                'datasets': [{
                    'label': 'Margen %',
                    'data': [p['margin'] for p in products],
                }]
            }
        elif report_type == 'CLIENTES' and 'top_clients' in data:
            clients = data['top_clients'][:10]
            return {
                'type': 'bar',
                'labels': [c['name'] for c in clients],
                'datasets': [{
                    'label': 'Total Gastado',
                    'data': [float(c['total_spent'] or 0) for c in clients],
                }]
            }
        elif report_type == 'DESPACHOS' and 'by_driver' in data:
            drivers = data['by_driver'][:10]
            return {
                'type': 'bar',
                'labels': [f"{d['route__driver__user__first_name']} {d['route__driver__user__last_name']}" for d in drivers],
                'datasets': [{
                    'label': 'Entregas',
                    'data': [d['count'] for d in drivers],
                }]
            }
        return None

    def _get_report_data(self, report_type, filters):
        """Obtener datos para cada tipo de reporte"""
        date_from = filters.get('date_from')
        date_to = filters.get('date_to')

        if date_from:
            date_from = timezone.datetime.fromisoformat(date_from)
        if date_to:
            date_to = timezone.datetime.fromisoformat(date_to)

        if report_type == 'VENTAS':
            return self._sales_report(date_from, date_to)
        elif report_type == 'STOCK':
            return self._stock_report()
        elif report_type == 'PRODUCCION':
            return self._production_report(date_from, date_to)
        elif report_type == 'RENTABILIDAD':
            return self._profitability_report(date_from, date_to)
        elif report_type == 'CLIENTES':
            return self._clients_report(date_from, date_to)
        elif report_type == 'DESPACHOS':
            return self._dispatches_report(date_from, date_to)
        elif report_type == 'PAGOS':
            return self._payments_report(date_from, date_to)
        return {'results': [], 'kpis': {}}

    def _sales_report(self, date_from, date_to):
        qs = Order.objects.exclude(status=OrderStatus.CANCELADO)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        total_sales = qs.aggregate(total=Sum('total'), count=Count('id'))
        by_status = qs.values('status').annotate(count=Count('id'), total=Sum('total'))
        by_day = qs.annotate(date=TruncDate('created_at')).values('date').annotate(total=Sum('total'), count=Count('id')).order_by('date')

        results = []
        for d in by_day:
            tot = float(d['total'] or 0)
            cnt = int(d['count'] or 0)
            avg = round(tot / cnt, 2) if cnt else 0
            day_orders = qs.filter(created_at__date=d['date'])
            webpay = float(Payment.objects.filter(order__in=day_orders, method='WEBPAY', status__in=['PAGADO_TOTAL', 'PAGADO_PARCIAL']).aggregate(s=Sum('amount'))['s'] or 0)
            cash = float(Payment.objects.filter(order__in=day_orders, method='EFECTIVO', status__in=['PAGADO_TOTAL', 'PAGADO_PARCIAL']).aggregate(s=Sum('amount'))['s'] or 0)
            results.append({
                'date': str(d['date']),
                'orders_count': cnt,
                'total_amount': tot,
                'avg_ticket': avg,
                'webpay_amount': webpay,
                'cash_amount': cash,
            })

        tot_amount = float(total_sales['total'] or 0)
        tot_count = int(total_sales['count'] or 0)
        webpay_tot = sum(r['webpay_amount'] for r in results)
        cash_tot = sum(r['cash_amount'] for r in results)

        kpis = {
            'total_revenue': tot_amount,
            'orders_count': tot_count,
            'avg_ticket': round(tot_amount / tot_count, 2) if tot_count else 0,
            'webpay_amount': webpay_tot,
            'cash_amount': cash_tot,
        }

        return {
            'summary': total_sales,
            'by_status': list(by_status),
            'by_day': list(by_day),
            'results': results,
            'kpis': kpis,
        }

    def _stock_report(self):
        ingredients = Ingredient.objects.filter(is_active=True).select_related('supplier')
        low_stock = ingredients.filter(current_stock__lte=F('min_stock'))
        out_of_stock = ingredients.filter(current_stock__lte=0)

        results = []
        for ing in ingredients:
            results.append({
                'id': ing.id,
                'name': ing.name,
                'unit': ing.unit,
                'current_stock': float(ing.current_stock),
                'min_stock': float(ing.min_stock),
                'unit_cost': float(ing.unit_cost or 0),
                'supplier_name': ing.supplier.name if ing.supplier else 'Sin proveedor',
            })

        kpis = {
            'critical_count': low_stock.count(),
            'out_of_stock_count': out_of_stock.count(),
            'total_value': round(sum(r['current_stock'] * r['unit_cost'] for r in results), 2),
        }

        return {
            'low_stock': list(low_stock.values('id', 'name', 'unit', 'current_stock', 'min_stock', 'unit_cost')),
            'out_of_stock': list(out_of_stock.values('id', 'name', 'unit')),
            'total_ingredients': ingredients.count(),
            'results': results,
            'kpis': kpis,
        }

    def _production_report(self, date_from, date_to):
        qs = ProductionCard.objects.select_related('column', 'order_item__product')
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        by_column = qs.values('column__name').annotate(count=Count('id'), total_servings=Sum('order_item__servings'))
        by_product = qs.values('order_item__product__name').annotate(count=Count('id')).order_by('-count')[:10]
        total_waste = qs.aggregate(total=Sum('waste_qty'))

        results = []
        for c in by_column:
            results.append({
                'column_name': c['column__name'] or 'Sin columna',
                'count': c['count'],
                'avg_days_in_column': 1.0,
                'total_servings': int(c['total_servings'] or 0),
            })

        kpis = {
            'production_cards': qs.count(),
            'completed_today': qs.filter(updated_at__date=timezone.now().date(), column__name__icontains='termin').count(),
            'overdue_count': 0,
        }

        return {
            'by_column': list(by_column),
            'top_products': list(by_product),
            'total_waste': total_waste['total'] or 0,
            'results': results,
            'kpis': kpis,
        }

    def _profitability_report(self, date_from, date_to):
        qs = OrderItem.objects.select_related('product__category', 'order')
        if date_from:
            qs = qs.filter(order__created_at__gte=date_from)
        if date_to:
            qs = qs.filter(order__created_at__lte=date_to)
        qs = qs.exclude(order__status=OrderStatus.CANCELADO)

        products_data = {}
        for item in qs:
            prod_id = item.product_id
            if prod_id not in products_data:
                category_name = item.product.category.name if item.product and item.product.category else 'General'
                products_data[prod_id] = {
                    'product_name': item.product.name if item.product else 'Producto',
                    'category_name': category_name,
                    'quantity': 0,
                    'revenue': 0,
                    'cost': 0,
                    'orders_count': 0,
                    'sale_price': float(item.product.sale_price if item.product and item.product.sale_price else (item.unit_price or 0)),
                }
            products_data[prod_id]['quantity'] += item.quantity
            products_data[prod_id]['revenue'] += float(item.subtotal)
            products_data[prod_id]['orders_count'] += 1

            for bom in (item.scaled_bom or []):
                products_data[prod_id]['cost'] += float(bom.get('estimated_cost', 0)) * item.quantity

        result = []
        for data in products_data.values():
            profit = data['revenue'] - data['cost']
            margin = (profit / data['revenue'] * 100) if data['revenue'] > 0 else 0
            bom_cost = (data['cost'] / data['quantity']) if data['quantity'] else 0
            result.append({
                'product_name': data['product_name'],
                'category_name': data['category_name'],
                'quantity_sold': data['quantity'],
                'quantity': data['quantity'],
                'revenue': round(data['revenue'], 2),
                'cost': round(data['cost'], 2),
                'margin': round(profit, 2),
                'profit': round(profit, 2),
                'margin_amount': round(profit, 2),
                'margin_percent': round(margin, 2),
                'sale_price': data['sale_price'],
                'bom_cost': round(bom_cost, 2),
                'orders_count': data['orders_count'],
            })

        result.sort(key=lambda x: x['revenue'], reverse=True)

        kpis = {
            'total_margin': round(sum(r['margin'] for r in result), 2),
            'avg_margin': round(sum(r['margin_percent'] for r in result) / len(result), 1) if result else 0,
            'products_sold': sum(r['quantity'] for r in result),
        }

        return {
            'by_product': result,
            'results': result,
            'kpis': kpis,
        }

    def _clients_report(self, date_from, date_to):
        qs = Client.objects.filter(is_active=True).annotate(
            orders_count=Count('orders'),
            spent_total=Sum('orders__total', filter=~Q(orders__status=OrderStatus.CANCELADO))
        ).order_by('-spent_total')[:50]

        results = []
        for c in qs:
            spent = float(c.spent_total or 0)
            cnt = c.orders_count or 0
            last_order = c.orders.order_by('-created_at').first()
            results.append({
                'id': c.id,
                'name': c.name,
                'email': c.email or '',
                'orders_count': cnt,
                'total_spent': spent,
                'avg_order': round(spent / cnt, 2) if cnt else 0,
                'last_order': str(last_order.created_at.date()) if last_order else '',
                'favorite_product': 'Surtido',
            })

        kpis = {
            'total_revenue': sum(r['total_spent'] for r in results),
            'orders_count': sum(r['orders_count'] for r in results),
            'avg_ticket': round(sum(r['total_spent'] for r in results) / (sum(r['orders_count'] for r in results) or 1), 2),
        }

        return {
            'top_clients': results,
            'results': results,
            'kpis': kpis,
        }

    def _dispatches_report(self, date_from, date_to):
        from apps.dispatch.models import Route, Dispatch
        routes_qs = Route.objects.all()
        if date_from:
            routes_qs = routes_qs.filter(date__gte=date_from)
        if date_to:
            routes_qs = routes_qs.filter(date__lte=date_to)

        results = []
        for r in routes_qs.prefetch_related('dispatches'):
            ds = list(r.dispatches.all())
            tot = len(ds)
            deliv = len([d for d in ds if d.status == 'ENTREGADO'])
            fail = len([d for d in ds if d.status == 'FALLIDO'])
            pend = len([d for d in ds if d.status in ['PENDIENTE', 'EN_RUTA']])
            results.append({
                'route_name': r.name,
                'date': str(r.date),
                'total_dispatches': tot,
                'delivered': deliv,
                'failed': fail,
                'pending': pend,
                'on_time_percent': round((deliv / tot * 100), 1) if tot > 0 else 0,
            })

        dispatches_qs = Dispatch.objects.all()
        if date_from:
            dispatches_qs = dispatches_qs.filter(route__date__gte=date_from)
        if date_to:
            dispatches_qs = dispatches_qs.filter(route__date__lte=date_to)

        by_status = dispatches_qs.values('status').annotate(count=Count('id'))
        by_driver = dispatches_qs.values('route__driver__user__first_name', 'route__driver__user__last_name').annotate(count=Count('id'))

        total_d = sum(r['total_dispatches'] for r in results)
        total_del = sum(r['delivered'] for r in results)

        kpis = {
            'delivered_count': total_del,
            'on_time_rate': round(total_del / (total_d or 1) * 100, 1),
        }

        return {
            'by_status': list(by_status),
            'by_driver': list(by_driver),
            'results': results,
            'kpis': kpis,
        }

    def _payments_report(self, date_from, date_to):
        qs = Payment.objects.all()
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        by_method = qs.values('method').annotate(count=Count('id'), total=Sum('amount'))
        results = []
        for m in by_method:
            cnt = m['count'] or 0
            tot = float(m['total'] or 0)
            success_cnt = qs.filter(method=m['method'], status__in=['PAGADO_TOTAL', 'PAGADO_PARCIAL']).count()
            results.append({
                'method': m['method'],
                'count': cnt,
                'total_amount': tot,
                'avg_amount': round(tot / cnt, 2) if cnt else 0,
                'success_rate': round((success_cnt / cnt * 100), 1) if cnt else 0,
            })

        total_cnt = qs.count()
        success_total = qs.filter(status__in=['PAGADO_TOTAL', 'PAGADO_PARCIAL']).count()
        total_rev = float(qs.filter(status__in=['PAGADO_TOTAL', 'PAGADO_PARCIAL']).aggregate(s=Sum('amount'))['s'] or 0)

        kpis = {
            'payments_count': total_cnt,
            'success_rate': round((success_total / (total_cnt or 1) * 100), 1),
            'total_revenue': total_rev,
        }

        return {
            'results': results,
            'kpis': kpis,
        }

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Datos para dashboard según rol
        GET /api/v1/reports/dashboard/
        """
        user = request.user
        data = {}

        if user.role == 'ADMIN':
            data = self._admin_dashboard()
        elif user.role == 'VENTAS':
            data = self._sales_dashboard()
        elif user.role == 'COCINERO':
            data = self._production_dashboard()
        elif user.role == 'BODEGA':
            data = self._warehouse_dashboard()
        elif user.role == 'REPARTIDOR':
            data = self._driver_dashboard(user)
        elif user.role == 'CLIENTE':
            data = self._client_dashboard(user)

        return Response(data)

    def _admin_dashboard(self):
        today = timezone.now().date()
        return {
            'kpis': {
                'orders_today': Order.objects.filter(created_at__date=today).count(),
                'pending_orders': Order.objects.filter(status__in=['COTIZACION', 'CONFIRMADO']).count(),
                'in_production': Order.objects.filter(status='EN_PRODUCCION').count(),
                'ready_to_dispatch': Order.objects.filter(status='LISTO').count(),
                'low_stock_ingredients': Ingredient.objects.filter(current_stock__lte=F('min_stock'), is_active=True).count(),
                'total_revenue_month': Order.objects.filter(
                    created_at__month=today.month,
                    status__in=['ENTREGADO', 'DESPACHADO']
                ).aggregate(total=Sum('total'))['total'] or 0,
            },
            'recent_orders': list(Order.objects.select_related('client').order_by('-created_at')[:5].values(
                'id', 'client__name', 'status', 'total', 'delivery_date'
            )),
        }

    def _sales_dashboard(self):
        return {
            'kpis': {
                'quotations_pending': 0,  # TODO
                'orders_confirmed_today': Order.objects.filter(
                    status='CONFIRMADO', confirmed_at__date=timezone.now().date()
                ).count(),
            },
        }

    def _production_dashboard(self):
        return {
            'kanban_summary': list(KanbanColumn.objects.annotate(
                count=Count('cards')
            ).values('name', 'count', 'color', 'order')),
            'my_tasks': [],
        }

    def _warehouse_dashboard(self):
        return {
            'low_stock_count': Ingredient.objects.filter(current_stock__lte=F('min_stock'), is_active=True).count(),
            'out_of_stock_count': Ingredient.objects.filter(current_stock__lte=0, is_active=True).count(),
            'pending_purchases': 0,  # TODO
        }

    def _driver_dashboard(self, user):
        if not hasattr(user, 'driver_profile'):
            return {}
        driver = user.driver_profile
        today = timezone.now().date()
        route = Route.objects.filter(driver=driver, date=today).first()
        return {
            'route': route.name if route else None,
            'pending_deliveries': Dispatch.objects.filter(
                route=route, status__in=['PENDIENTE', 'EN_RUTA']
            ).count() if route else 0,
            'completed_today': Dispatch.objects.filter(
                route=route, status='ENTREGADO', delivered_at__date=today
            ).count() if route else 0,
        }

    def _client_dashboard(self, user):
        # El Client tiene OneToOne con User en el campo 'client_profile'
        try:
            client = user.client_profile
        except Client.DoesNotExist:
            return {}
        return {
            'my_orders': list(Order.objects.filter(client=client).order_by('-created_at')[:5].values(
                'id', 'status', 'total', 'delivery_date'
            )),
            'pending_payments': list(Payment.objects.filter(
                order__client=client, status=PaymentStatus.PENDIENTE
            ).values('id', 'order__id', 'amount', 'created_at')),
        }