import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import ChatRoom, Message
from asgiref.sync import sync_to_async
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Get or create room and send room info
        room_info = await self.get_or_create_room()
        recent_messages = await self.get_recent_messages()
        
        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Successfully connected to room: {self.room_name}',
            'room': room_info,
            'recent_messages': recent_messages
        }))

        # Notify room about new user
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_activity',
                'message': 'A new user joined the chat',
                'activity_type': 'user_join',
                'timestamp': timezone.now().isoformat()
            }
        )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Notify room about user leaving
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_activity',
                'message': 'A user left the chat',
                'activity_type': 'user_leave',
                'timestamp': timezone.now().isoformat()
            }
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing_indicator(data)
            elif message_type == 'user_join':
                await self.handle_user_join(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format in message'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error processing message: {str(e)}'
            }))

    async def handle_chat_message(self, data):
        message_content = data.get('message', '').strip()
        user = data.get('user', 'Anonymous').strip()
        
        if not message_content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message content cannot be empty'
            }))
            return
            
        if not user:
            user = 'Anonymous'

        # Save message to database
        saved_message = await self.save_message(user, message_content)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'user': user,
                'message_id': saved_message.id,
                'timestamp': saved_message.timestamp.isoformat(),
                'room_name': self.room_name
            }
        )

    async def handle_typing_indicator(self, data):
        user = data.get('user', 'Anonymous')
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': user,
                'is_typing': is_typing,
                'timestamp': timezone.now().isoformat()
            }
        )

    async def handle_user_join(self, data):
        user = data.get('user', 'Anonymous')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_activity',
                'message': f'{user} joined the chat',
                'activity_type': 'user_join',
                'user': user,
                'timestamp': timezone.now().isoformat()
            }
        )

    # WebSocket event handlers
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user': event['user'],
            'message_id': event['message_id'],
            'timestamp': event['timestamp'],
            'room_name': event['room_name']
        }))

    async def user_activity(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_activity',
            'message': event['message'],
            'activity_type': event['activity_type'],
            'user': event.get('user', 'System'),
            'timestamp': event['timestamp']
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user': event['user'],
            'is_typing': event['is_typing'],
            'timestamp': event['timestamp']
        }))

    # Database operations
    @sync_to_async
    def get_or_create_room(self):
        room, created = ChatRoom.objects.get_or_create(name=self.room_name)
        return {
            'id': room.id,
            'name': room.name,
            'created_at': room.created_at.isoformat(),
            'message_count': room.messages.count()
        }

    @sync_to_async
    def get_recent_messages(self, limit=20):
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            messages = room.messages.all().order_by('-timestamp')[:limit]
            return [
                {
                    'id': msg.id,
                    'user': msg.user,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        except ChatRoom.DoesNotExist:
            return []

    @sync_to_async
    def save_message(self, user, content):
        room, created = ChatRoom.objects.get_or_create(name=self.room_name)
        return Message.objects.create(room=room, user=user, content=content)