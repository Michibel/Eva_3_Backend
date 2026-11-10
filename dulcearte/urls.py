"""
Configuración de URLs principal para Dulce Arte
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# Importar ViewSets de las apps
from apps.accounts.views import UserViewSet
from apps.clients.views import ClientViewSet, ClientPreferenceViewSet
from apps.products.views import CategoryViewSet, ProductViewSet, BOMItemViewSet
from apps.ingredients.views import SupplierViewSet, IngredientViewSet, StockMovementViewSet, PurchaseOrderViewSet
from apps.orders.views import OrderViewSet, OrderItemViewSet, PaymentViewSet, QuotationViewSet
from apps.production.views import KanbanColumnViewSet, ProductionCardViewSet, CardMovementViewSet
from apps.dispatch.views import DriverViewSet, RouteViewSet, DispatchViewSet
from apps.payments.views import WebPayTransactionViewSet
from apps.reports.views import DashboardWidgetViewSet, ReportViewSet

# Router principal de la API
router = routers.DefaultRouter()

# Reports
router.register(r'dashboard-widgets', DashboardWidgetViewSet, basename='dashboard-widget')
# Note: reports are included from apps.reports.urls to have the dashboard endpoint

# Accounts
router.register(r'users', UserViewSet, basename='user')

# Clients
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'client-preferences', ClientPreferenceViewSet, basename='client-preference')

# Products
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'bom-items', BOMItemViewSet, basename='bom-item')

# Ingredients
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'stock-movements', StockMovementViewSet, basename='stock-movement')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')

# Orders
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-items', OrderItemViewSet, basename='order-item')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'quotations', QuotationViewSet, basename='quotation')

# Production
router.register(r'kanban-columns', KanbanColumnViewSet, basename='kanban-column')
router.register(r'production-cards', ProductionCardViewSet, basename='production-card')
router.register(r'card-movements', CardMovementViewSet, basename='card-movement')

# Dispatch
router.register(r'drivers', DriverViewSet, basename='driver')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'dispatches', DispatchViewSet, basename='dispatch')

# Payments
router.register(r'webpay-transactions', WebPayTransactionViewSet, basename='webpay-transaction')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Reports (with dashboard endpoint) - MUST come before router
    path('api/v1/reports/', include('apps.reports.urls')),

    # Accounts API (JWT tokens via session)
    path('api/v1/accounts/', include('apps.accounts.urls')),

    # JWT Auth
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # API v1 (router) - MUST come after specific paths
    path('api/v1/', include(router.urls)),

    # Frontend (Templates)
    path('', include('apps.frontend.urls')),
]

# Media files en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)