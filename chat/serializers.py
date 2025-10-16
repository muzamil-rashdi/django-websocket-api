from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ChatRoom, Message, RoomParticipant

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class MessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    timestamp = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'room', 'room_name', 'user', 'user_id', 'content', 'timestamp']
        read_only_fields = ['timestamp']

    def create(self, validated_data):
        validated_data['user'] = User.objects.get(id=validated_data['user_id'])
        return super().create(validated_data)

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

class ChatRoomDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    participants = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'chat_type', 'created_at', 'message_count', 
            'participants', 'created_by', 'messages'
        ]
        read_only_fields = ['created_at']

class PrivateChatCreateSerializer(serializers.Serializer):
    participant_id = serializers.IntegerField()

class RoomParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = RoomParticipant
        fields = ['user', 'joined_at', 'is_online']