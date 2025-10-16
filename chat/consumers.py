import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("🔄 WebSocket connect attempt received")
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        print(f"🎯 Room name: {self.room_name}")
        print(f"🎯 Room group name: {self.room_group_name}")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print("✅ WebSocket connection accepted")

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Successfully connected to room: {self.room_name}'
        }))

    async def disconnect(self, close_code):
        print(f"🔌 WebSocket disconnected with code: {close_code}")
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        print(f"📥 Received message: {text_data}")
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')
            user = text_data_json.get('user', 'Anonymous')
            message_type = text_data_json.get('type', 'chat_message')

            if message_type == 'chat_message':
                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'user': user
                    }
                )
            elif message_type == 'typing':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'user': user,
                        'is_typing': text_data_json.get('is_typing', False)
                    }
                )

        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    # Receive message from room group
    async def chat_message(self, event):
        print(f"📤 Sending chat message to client: {event}")
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user': event['user']
        }))

    async def typing_indicator(self, event):
        print(f"📤 Sending typing indicator: {event}")
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user': event['user'],
            'is_typing': event['is_typing']
        }))