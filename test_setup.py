import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_app.settings')
django.setup()

# Test basic Django setup
from django.apps import apps
print("✅ Django apps loaded:")
for app in apps.get_app_configs():
    print(f"  - {app.name}")

# Test models
from chat.models import ChatRoom, Message
print("✅ Models imported successfully")

# Test channels
from channels.layers import get_channel_layer
channel_layer = get_channel_layer()
print(f"✅ Channel layer: {channel_layer}")

print("🎉 All imports successful!")