from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Q, Prefetch, Subquery, OuterRef
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from .models import ChatRoom, Message, RoomParticipant
from .serializers import (
    ChatRoomListSerializer, MessageSerializer, ChatRoomDetailSerializer,
    PrivateChatCreateSerializer, UserSerializer
)

class ChatRoomViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Get the latest message for each room using subquery
        latest_message_subquery = Message.objects.filter(
            room=OuterRef('pk')
        ).order_by('-timestamp').values('content', 'user__username', 'timestamp')[:1]
        
        queryset = ChatRoom.objects.filter(
            participants=user
        ).annotate(
            participant_count=Count('participants'),
            last_message_content=Subquery(latest_message_subquery.values('content')),
            last_message_user=Subquery(latest_message_subquery.values('user__username')),
            last_message_time=Subquery(latest_message_subquery.values('timestamp'))
        ).order_by('-last_message_time', '-created_at')
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatRoomDetailSerializer
        return ChatRoomListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        participant_ids = request.data.get('participants', [])
        participant_ids.append(request.user.id)
        
        participants = User.objects.filter(id__in=participant_ids).distinct()
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            chat_room = serializer.save(created_by=request.user)
            chat_room.participants.set(participants)
            
            # Return the detailed view
            detail_serializer = ChatRoomDetailSerializer(chat_room, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def my_chats(self, request):
        """Get all chats for current user with last message"""
        chats = self.get_queryset()
        serializer = self.get_serializer(chats, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_private_chat(self, request):
        """Create or get existing private chat between two users"""
        serializer = PrivateChatCreateSerializer(data=request.data)
        if serializer.is_valid():
            participant_id = serializer.validated_data['participant_id']
            
            if participant_id == request.user.id:
                return Response(
                    {'error': 'Cannot create private chat with yourself'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                other_user = User.objects.get(id=participant_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if private chat already exists
            existing_chat = ChatRoom.objects.filter(
                chat_type='private',
                participants=request.user
            ).filter(
                participants=other_user
            ).annotate(
                participant_count=Count('participants')
            ).filter(participant_count=2).first()
            
            if existing_chat:
                serializer = ChatRoomDetailSerializer(existing_chat, context={'request': request})
                return Response(serializer.data)
            
            # Create new private chat
            chat_room = ChatRoom.objects.create(
                chat_type='private',
                created_by=request.user
            )
            chat_room.participants.add(request.user, other_user)
            
            serializer = ChatRoomDetailSerializer(chat_room, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def available_users(self, request):
        """Get list of users available for chatting"""
        current_user = request.user
        users = User.objects.exclude(id=current_user.id)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages for a specific room"""
        room = self.get_object()
        messages = room.messages.all().select_related('user').order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.all().select_related('user', 'room')
    serializer_class = MessageSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Message.objects.filter(
            room__participants=user
        ).select_related('user', 'room')
        
        room_id = self.request.query_params.get('room_id')
        if room_id:
            queryset = queryset.filter(room_id=room_id)
            
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        # Verify user has access to the room
        room = serializer.validated_data['room']
        if not room.participants.filter(id=self.request.user.id).exists():
            raise permissions.PermissionDenied("You don't have access to this room")
        
        serializer.save(user=self.request.user)

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