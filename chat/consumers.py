import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("=" * 60)
        print("🔄 WebSocket CONNECT attempt - DEBUG VERSION")
        print("=" * 60)
        
        # Debug scope information
        print(f"📋 Scope keys: {list(self.scope.keys())}")
        print(f"👤 User in scope: {self.scope.get('user')}")
        print(f"🔗 Path: {self.scope.get('path')}")
        print(f"📝 Headers: {self.scope.get('headers')}")
        
        # Get room name from URL
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        print(f"🎯 Room name: {self.room_name}")
        print(f"🎯 Room group name: {self.room_group_name}")

        # Get user from scope
        self.user = self.scope.get("user")
        print(f"👤 User object: {self.user}")
        print(f"🔐 Is authenticated: {getattr(self.user, 'is_authenticated', 'NO USER OBJECT')}")
        
        # Check query string for token
        query_string = self.scope.get('query_string', b'').decode()
        print(f"🔍 Query string: {query_string}")
        
        # If user is anonymous, try to authenticate via token
        if not self.user or self.user.is_anonymous:
            print("🔑 Attempting token authentication...")
            if 'token=' in query_string:
                token = query_string.split('token=')[1].split('&')[0]
                print(f"🔑 Token found: {token[:50]}...")
                user = await self.get_user_from_token(token)
                if user:
                    self.user = user
                    self.scope['user'] = user
                    print(f"✅ Token auth successful! User: {user.username}")
                else:
                    print("❌ Token auth failed")
            else:
                print("❌ No token found in query string")
        
        # Final user check
        if not self.user or self.user.is_anonymous:
            print("❌ REJECTING: User is anonymous or not set")
            await self.close(code=4001)  # Custom close code for debugging
            return

        print(f"✅ User authenticated: {self.user.username} (ID: {self.user.id})")

        # Verify room access
        has_access = await self.verify_room_access()
        print(f"🔐 Room access: {has_access}")
        
        if not has_access:
            print("❌ REJECTING: No room access")
            await self.close(code=4002)  # Custom close code for no access
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print("✅✅✅ WebSocket connection ACCEPTED ✅✅✅")

        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Successfully connected to room: {self.room_name}',
            'user': self.user.username,
            'user_id': self.user.id
        }))

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Get user from JWT token"""
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            print(f"🔐 Validating token: {token[:50]}...")
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            print(f"🔐 Token validated, user_id: {user_id}")
            user = User.objects.get(id=user_id)
            print(f"🔐 User found: {user.username}")
            return user
        except Exception as e:
            print(f"❌ Token validation failed: {str(e)}")
            return None

    @database_sync_to_async
    def verify_room_access(self):
        """Verify user has access to this room"""
        try:
            print(f"🔐 Checking room access for user {self.user.id} in room {self.room_name}")
            room = ChatRoom.objects.get(id=int(self.room_name))
            has_access = room.participants.filter(id=self.user.id).exists()
            print(f"🔐 Room '{room.name}' access: {has_access}")
            return has_access
        except ChatRoom.DoesNotExist:
            print(f"❌ Room {self.room_name} does not exist")
            return False
        except Exception as e:
            print(f"❌ Room access error: {str(e)}")
            return False

    async def disconnect(self, close_code):
        print(f"🔌 WebSocket DISCONNECTED with code: {close_code}")
        if hasattr(self, 'room_group_name') and hasattr(self, 'channel_layer'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        print(f"📥 Received message: {text_data}")
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')
            
            if message:
                # Save message to database
                await self.save_message(message)
                
                # Broadcast to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'user': self.user.username,
                        'user_id': self.user.id
                    }
                )
        except Exception as e:
            print(f"❌ Error receiving message: {str(e)}")

    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        try:
            room = ChatRoom.objects.get(id=int(self.room_name))
            message = Message.objects.create(
                room=room,
                user=self.user,
                content=content
            )
            print(f"💾 Saved message: '{content}' by {self.user.username}")
            return message
        except Exception as e:
            print(f"❌ Error saving message: {str(e)}")
            return None

    async def chat_message(self, event):
        """Handle chat_message type events"""
        print(f"📤 Broadcasting message: {event['user']}: {event['message']}")
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user': event['user'],
            'user_id': event['user_id']
        }))