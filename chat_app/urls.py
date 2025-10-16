from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

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
            'chat_rooms': '/api/chat/rooms/',
            'chat_messages': '/api/chat/messages/',
            'websocket_endpoint': 'ws://localhost:8000/ws/chat/{room_name}/'
        },
        'webSocket_events': {
            'join': 'Automatically on connection',
            'chat_message': 'Send/receive messages',
            'typing': 'Typing indicators',
            'user_activity': 'User join/leave notifications'
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', include('chat.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('', api_root, name='api-root'),
]

# Include WebSocket URLs for Django Channels
from django.urls import re_path
from chat.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>\w+)/$', ChatConsumer.as_asgi()),
]