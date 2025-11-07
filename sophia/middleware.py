# sophia/middleware.py
class EscolaMiddleware:
    """Middleware para adicionar escola_id automaticamente em todas as requisições"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Pega escola_id do header ou query param
        escola_id = (
            request.headers.get('X-Escola-ID') or 
            request.GET.get('escola_id') or
            request.POST.get('escola_id')
        )
        
        # Adiciona ao request para uso nas views
        request.escola_id = escola_id
        
        response = self.get_response(request)
        return response