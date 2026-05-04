from rest_framework.viewsets import ModelViewSet


class TenantViewSetMixin:
    """
    Filtra el queryset al negocio del usuario autenticado.
    Heredar antes de ModelViewSet.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(negocio=self.request.user.negocio)
