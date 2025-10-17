from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rooms', views.ChatRoomViewSet, basename='chatroom')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.register_user, name='register'),
    path('rooms/create_private_chat/', views.ChatRoomViewSet.as_view({'post': 'create_private_chat'}), name='create-private-chat'),
    path('rooms/my_chats/', views.ChatRoomViewSet.as_view({'get': 'my_chats'}), name='my-chats'),
    path('rooms/available_users/', views.ChatRoomViewSet.as_view({'get': 'available_users'}), name='available-users'),
]