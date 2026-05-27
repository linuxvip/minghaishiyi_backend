from minghub.context import current_user


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user and request.user.is_authenticated:
            current_user.set(request.user)
        response = self.get_response(request)
        return response
