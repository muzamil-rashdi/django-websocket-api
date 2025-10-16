from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# API Documentation
schema_view = get_schema_view(
   openapi.Info(
      title="Chat WebSocket API",
      default_version='v1',
      description="Real-time chat API with WebSocket support",
      contact=openapi.Contact(email="admin@chatapi.com"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

def api_root(request):
    return JsonResponse({
        'message': 'Django REST Framework + WebSocket Chat API',
        'endpoints': {
            'admin': '/admin/',
            'api_documentation': '/swagger/',
            'auth_token': '/api/auth/token/',
            'auth_refresh': '/api/auth/token/refresh/',
            'chat_rooms': '/api/chat/rooms/',
            'chat_messages': '/api/chat/messages/',
            'websocket_endpoint': 'ws://localhost:8000/ws/chat/{room_id}/'
        },
        'webSocket_events': {
            'join': 'Automatically on connection',
            'chat_message': 'Send/receive messages',
            'typing': 'Typing indicators',
            'user_activity': 'User join/leave notifications',
            'active_users': 'Get list of active users'
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', include('chat.urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('', api_root, name='api-root'),
]