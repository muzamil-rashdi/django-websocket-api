from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class ChatRoom(models.Model):
    CHAT_TYPES = (
        ('group', 'Group Chat'),
        ('private', 'Private Chat'),
    )
    
    name = models.CharField(max_length=100, blank=True)
    chat_type = models.CharField(max_length=10, choices=CHAT_TYPES, default='group')
    participants = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.chat_type == 'private':
            participants = list(self.participants.all()[:2])
            if len(participants) == 2:
                usernames = sorted([p.username for p in participants])
                return f"Private: {usernames[0]} & {usernames[1]}"
        return self.name or f"Group Chat {self.id}"

    def get_display_name(self, user=None):
        """Get display name for the chat room"""
        if self.chat_type == 'private':
            other_users = self.participants.exclude(id=user.id) if user else self.participants.all()
            if other_users.exists():
                return f"Chat with {other_users.first().username}"
        return self.name or "Unnamed Group Chat"

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'{self.user.username}: {self.content[:50]}'

class RoomParticipant(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='active_participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_online = models.BooleanField(default=False)

    class Meta:
        unique_together = ['room', 'user']

    def __str__(self):
        return f"{self.user.username} in {self.room.id}"