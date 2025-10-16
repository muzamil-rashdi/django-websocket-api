from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Q
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from .models import ChatRoom, Message, RoomParticipant
from .serializers import (
    ChatRoomSerializer, MessageSerializer, ChatRoomDetailSerializer,
    PrivateChatCreateSerializer, UserSerializer
)
class IsParticipantOrCreator(permissions.BasePermission):
    """Custom permission to only allow participants or creator of a chat room"""
    def has_object_permission(self, request, view, obj):
        return obj.participants.filter(id=request.user.id).exists() or obj.created_by == request.user

class ChatRoomViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsParticipantOrCreator]
    
    def get_queryset(self):
        user = self.request.user
        queryset = ChatRoom.objects.filter(participants=user).annotate(
            message_count=Count('messages'),
            participant_count=Count('participants')
        )
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatRoomDetailSerializer
        return ChatRoomSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        # Handle participant IDs
        participant_ids = request.data.get('participant_ids', [])
        participant_ids.append(request.user.id)  # Always include creator
        
        # Get participant objects
        participants = User.objects.filter(id__in=participant_ids).distinct()
        
        # For group chats, check name uniqueness
        if request.data.get('chat_type') == 'group':
            name = request.data.get('name')
            if name and ChatRoom.objects.filter(name=name, chat_type='group').exists():
                return Response(
                    {'error': 'Group chat with this name already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create serializer with context
        serializer = self.get_serializer(data=request.data)
        serializer.context['participants'] = participants  # Pass participants via context
        
        if serializer.is_valid():
            # Create the room with current user as creator
            chat_room = serializer.save(created_by=request.user)
            
            return Response(ChatRoomDetailSerializer(chat_room).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages for a specific room"""
        room = self.get_object()
        messages = room.messages.all().select_related('user').order_by('timestamp')
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def active_users(self, request, pk=None):
        """Get active users in the room"""
        room = self.get_object()
        active_users = RoomParticipant.objects.filter(room=room, is_online=True).select_related('user')
        serializer = UserSerializer([participant.user for participant in active_users], many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search chat rooms by name"""
        query = request.query_params.get('q', '')
        if query:
            rooms = ChatRoom.objects.filter(
                Q(name__icontains=query) & 
                Q(participants=request.user)
            ).annotate(
                message_count=Count('messages'),
                participant_count=Count('participants')
            )
            serializer = self.get_serializer(rooms, many=True)
            return Response(serializer.data)
        return Response([])

    @action(detail=False, methods=['post'])
    def create_private_chat(self, request):
        """Create or get existing private chat between two users"""
        serializer = PrivateChatCreateSerializer(data=request.data)
        if serializer.is_valid():
            participant_id = serializer.validated_data['participant_id']
            
            # Check if private chat already exists
            existing_chat = ChatRoom.objects.filter(
                chat_type='private',
                participants=request.user
            ).filter(
                participants=participant_id
            ).distinct().first()
            
            if existing_chat:
                return Response(ChatRoomDetailSerializer(existing_chat).data)
            
            # Create new private chat - FIRST save without participants
            chat_room = ChatRoom.objects.create(
                chat_type='private',
                created_by=request.user
            )
            
            # THEN add participants after the room has been saved
            other_user = User.objects.get(id=participant_id)
            chat_room.participants.add(request.user, other_user)
            
            return Response(ChatRoomDetailSerializer(chat_room).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.all().select_related('user', 'room')
    serializer_class = MessageSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Message.objects.filter(room__participants=user).select_related('user', 'room')
        room_id = self.request.query_params.get('room_id')
        user_id = self.request.query_params.get('user_id')
        
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Default to current user as participant
        context['participants'] = [self.request.user]
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Ensure the room exists and user is participant
            room_id = serializer.validated_data['room'].id
            if not ChatRoom.objects.filter(id=room_id, participants=request.user).exists():
                return Response(
                    {'error': 'Chat room does not exist or you are not a participant'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent messages across all rooms user participates in"""
        limit = int(request.query_params.get('limit', 50))
        messages = Message.objects.filter(
            room__participants=request.user
        ).select_related('user', 'room').order_by('-timestamp')[:limit]
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get all messages by a specific user in rooms you share"""
        username = request.query_params.get('username')
        if not username:
            return Response(
                {'error': 'username parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        messages = Message.objects.filter(
            user__username=username,
            room__participants=request.user
        ).select_related('user', 'room')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Simple user registration endpoint"""
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )
    
    return Response({
        'message': 'User created successfully',
        'user_id': user.id,
        'username': user.username
    }, status=status.HTTP_201_CREATED)