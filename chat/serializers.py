from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ChatRoom, Message, RoomParticipant

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ChatRoom, Message, RoomParticipant

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class MessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    timestamp = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'room', 'user', 'content', 'timestamp']
        read_only_fields = ['timestamp']

class ChatRoomListSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participant_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'chat_type', 'display_name', 'last_message', 'unread_count', 'participant_count', 'created_at']

    def get_display_name(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        
        if obj.chat_type == 'private':
            other_users = obj.participants.exclude(id=user.id) if user else obj.participants.all()
            if other_users.exists():
                return f"Chat with {other_users.first().username}"
        return obj.name or "Group Chat"

    def get_last_message(self, obj):
        # Use annotated fields if available
        if hasattr(obj, 'last_message_content') and obj.last_message_content:
            return {
                'content': obj.last_message_content[:50] + '...' if len(obj.last_message_content) > 50 else obj.last_message_content,
                'user': obj.last_message_user,
                'timestamp': obj.last_message_time
            }
        
        # Fallback to querying the last message
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'content': last_msg.content[:50] + '...' if len(last_msg.content) > 50 else last_msg.content,
                'user': last_msg.user.username,
                'timestamp': last_msg.timestamp
            }
        return None

    def get_unread_count(self, obj):
        return 0  # You can implement this later

class ChatRoomDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    display_name = serializers.SerializerMethodField()
    participants = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'chat_type', 'display_name', 'participants', 'created_by', 'messages', 'created_at']

    def get_display_name(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        
        if obj.chat_type == 'private':
            other_users = obj.participants.exclude(id=user.id) if user else obj.participants.all()
            if other_users.exists():
                return f"Chat with {other_users.first().username}"
        return obj.name or "Group Chat"

class PrivateChatCreateSerializer(serializers.Serializer):
    participant_id = serializers.IntegerField()

class RoomParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = RoomParticipant
        fields = ['user', 'joined_at', 'is_online']




class ChatRoomSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True)
    participant_count = serializers.IntegerField(read_only=True)
    created_by = UserSerializer(read_only=True)
    participants = UserSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'chat_type', 'created_at', 'message_count', 
            'participant_count', 'created_by', 'participants'
        ]
        read_only_fields = ['created_at', 'created_by']

    def create(self, validated_data):
        # Get participants from context (passed from view)
        participants = self.context.get('participants', [])
        
        # Create the room
        chat_room = ChatRoom.objects.create(**validated_data)
        
        # Add participants
        if participants:
            chat_room.participants.add(*participants)
        
        return chat_room