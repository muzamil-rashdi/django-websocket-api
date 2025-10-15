from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer, ChatRoomDetailSerializer

class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all().annotate(
        message_count=Count('messages')
    )
    serializer_class = ChatRoomSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatRoomDetailSerializer
        return ChatRoomSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check if room with same name exists
            name = serializer.validated_data['name']
            if ChatRoom.objects.filter(name=name).exists():
                return Response(
                    {'error': 'Chat room with this name already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages for a specific room"""
        room = self.get_object()
        messages = room.messages.all().order_by('timestamp')
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search chat rooms by name"""
        query = request.query_params.get('q', '')
        if query:
            rooms = ChatRoom.objects.filter(
                Q(name__icontains=query)
            ).annotate(message_count=Count('messages'))
            serializer = self.get_serializer(rooms, many=True)
            return Response(serializer.data)
        return Response([])

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().select_related('room')
    serializer_class = MessageSerializer

    def get_queryset(self):
        queryset = Message.objects.all().select_related('room')
        room_id = self.request.query_params.get('room_id')
        user = self.request.query_params.get('user')
        
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        if user:
            queryset = queryset.filter(user__icontains=user)
            
        return queryset.order_by('-timestamp')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Ensure the room exists
            room_id = serializer.validated_data['room'].id
            if not ChatRoom.objects.filter(id=room_id).exists():
                return Response(
                    {'error': 'Chat room does not exist'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent messages across all rooms"""
        limit = int(request.query_params.get('limit', 50))
        messages = Message.objects.all().select_related('room').order_by('-timestamp')[:limit]
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get all messages by a specific user"""
        username = request.query_params.get('username')
        if not username:
            return Response(
                {'error': 'username parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        messages = Message.objects.filter(user__icontains=username).select_related('room')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)