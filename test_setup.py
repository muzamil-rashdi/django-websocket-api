import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_app.settings')
django.setup()

# Test if consumer can be imported
try:
    from chat.consumers import ChatConsumer
    print("✅ Consumer imported successfully")
    
    # Test if models work
    from chat.models import ChatRoom
    from django.contrib.auth.models import User
    
    user = User.objects.get(username='muzamil1')
    room = ChatRoom.objects.get(id=2)
    print(f"✅ Models work: User {user.username}, Room {room.name}")
    
except Exception as e:
    print(f"❌ Error: {e}")