from django.utils.deprecation import MiddlewareMixin


class DebugHeadersMiddleware(MiddlewareMixin):
    def process_request(self, request):
        return
        print("HTTP Headers: " + str(request.META) + "\n")

        print("Host: " + str(request.META.get('HTTP_HOST')) + "\n")
