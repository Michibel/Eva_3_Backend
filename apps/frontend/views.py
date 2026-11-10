"""
Views para frontend (templates HTML)
Todas las vistas renderizan templates que consumen la API via fetch/JS
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


class LoginRequiredMixinCustom(LoginRequiredMixin):
    """Mixin que redirige al login si no autenticado"""
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(self.login_url)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(never_cache, name='dispatch')
class DashboardView(LoginRequiredMixinCustom, TemplateView):
    """Dashboard principal según rol"""
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Dashboard'
        return context


@method_decorator(never_cache, name='dispatch')
class ClientsView(LoginRequiredMixinCustom, TemplateView):
    """Gestión de clientes"""
    template_name = 'clients/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Clientes'
        return context


@method_decorator(never_cache, name='dispatch')
class ProductsView(LoginRequiredMixinCustom, TemplateView):
    """Gestión de productos/recetas"""
    template_name = 'products/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Productos / Recetas'
        return context


@method_decorator(never_cache, name='dispatch')
class IngredientsView(LoginRequiredMixinCustom, TemplateView):
    """Gestión de insumos/stock"""
    template_name = 'ingredients/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Insumos / Stock'
        return context


@method_decorator(never_cache, name='dispatch')
class OrdersView(LoginRequiredMixinCustom, TemplateView):
    """Gestión de pedidos y cotizaciones"""
    template_name = 'orders/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Pedidos'
        return context


@method_decorator(never_cache, name='dispatch')
class ProductionView(LoginRequiredMixinCustom, TemplateView):
    """Kanban de producción"""
    template_name = 'production/kanban.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Producción (Kanban)'
        return context


@method_decorator(never_cache, name='dispatch')
class DispatchView(LoginRequiredMixinCustom, TemplateView):
    """Gestión de despachos y rutas"""
    template_name = 'dispatch/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Despachos / Rutas'
        return context


@method_decorator(never_cache, name='dispatch')
class PaymentsView(LoginRequiredMixinCustom, TemplateView):
    """Pagos y WebPay"""
    template_name = 'payments/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Pagos'
        return context


@method_decorator(never_cache, name='dispatch')
class ReportsView(LoginRequiredMixinCustom, TemplateView):
    """Reportes y dashboards"""
    template_name = 'reports/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Reportes'
        return context


@method_decorator(never_cache, name='dispatch')
class ClientPortalView(LoginRequiredMixinCustom, TemplateView):
    """Portal del cliente"""
    template_name = 'client/portal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Mi Cuenta'
        return context


# Vistas de autenticación (sin LoginRequiredMixin)
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic.edit import FormView
from django.contrib.auth.forms import PasswordChangeForm
from apps.accounts.forms import CustomUserCreationForm
from django.contrib.auth import login
import requests
from django.conf import settings


class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_valid(self, form):
        """Al hacer login exitoso, también obtener tokens JWT"""
        response = super().form_valid(form)

        # Obtener tokens JWT via API interna
        try:
            # Usar el endpoint JWT directamente
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(self.request.user)

            # Guardar tokens en la sesión para que el template los use
            self.request.session['jwt_access'] = str(refresh.access_token)
            self.request.session['jwt_refresh'] = str(refresh)
        except Exception:
            pass  # Si falla, el JS intentará obtenerlos via API

        return response


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')

    def get(self, request, *args, **kwargs):
        """Permitir cierre de sesión vía GET y redirigir al login"""
        return self.post(request, *args, **kwargs)


class RegisterView(FormView):
    template_name = 'auth/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class PasswordChangeView(LoginRequiredMixinCustom, FormView):
    template_name = 'auth/password_change.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)