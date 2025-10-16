from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class ChatRoom(models.Model):
    CHAT_TYPES = (
        ('group', 'Group Chat'),
        ('private', 'Private Chat'),
    )
    
    name = models.CharField(max_length=100, blank=True)  # Optional for private chats
    chat_type = models.CharField(max_length=10, choices=CHAT_TYPES, default='group')
    participants = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['chat_type', 'name'],
                name='unique_group_chat_name',
                condition=models.Q(chat_type='group')
            )
        ]

    def clean(self):
        # Only validate participants count if the room has been saved (has an ID)
        if self.pk and self.chat_type == 'private':
            if self.participants.count() != 2:
                raise ValidationError('Private chats must have exactly 2 participants')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        if not self.pk:  # Object hasn't been saved yet
            if self.chat_type == 'private':
                return "New Private Chat"
            return f"New Chat: {self.name}" if self.name else "New Chat"
        
        if self.chat_type == 'private':
            participants = list(self.participants.all()[:3])  # Limit to avoid performance issues
            if len(participants) == 2:
                return f"Private: {participants[0].username} & {participants[1].username}"
            elif participants:
                return f"Private: {', '.join(p.username for p in participants)}"
            else:
                return "Private Chat (no participants)"
        return self.name or f"Group Chat {self.id}"

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
    """Track active users in rooms"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='active_participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_online = models.BooleanField(default=True)

    class Meta:
        unique_together = ['room', 'user']

    def __str__(self):
        return f"{self.user.username} in {self.room.id if self.room.pk else 'new room'}"