from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings # For ForeignKey to settings.AUTH_USER_MODEL

# Remove the old Friends field from User model if we are replacing it with a Friendship model
# We will create a UserProfile model instead for profile picture and other settings.

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, verbose_name="Фото профиля")
    friends = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='friend_profiles', blank=True, verbose_name="Друзья")
    
    PRIVACY_CHOICES = [
        ('everyone', 'Все'),
        ('friends', 'Только друзья'),
        ('only_me', 'Только я'),
    ]
    # Based on your Profile modal screenshot
    privacy_schedule_visibility = models.CharField(
        max_length=10, choices=PRIVACY_CHOICES, default='friends', verbose_name="Кто видит личное расписание"
    )
    privacy_can_invite_to_event = models.CharField(
        max_length=10, choices=PRIVACY_CHOICES[:-1], default='friends', verbose_name="Кто может приглашать на мероприятия" # Exclude 'only_me'
    )
    privacy_can_send_message = models.CharField(
        max_length=10, choices=PRIVACY_CHOICES[:-1], default='friends', verbose_name="Кто может отправлять сообщения" # Exclude 'only_me'
    )
    privacy_profile_photo_visibility = models.CharField(
        max_length=10, choices=PRIVACY_CHOICES, default='everyone', verbose_name="Кто видит фото профиля"
    )
    interface_language = models.CharField(max_length=10, default='Русский', verbose_name="Язык интерфейса")

    def __str__(self):
        return f"Профиль пользователя {self.user.username}"

class User(AbstractUser):
    # The old Friends field is removed. We will use the Friendship model below.
    # Existing methods like create_event and delete_event can remain,
    # but their interaction with Participants might change based on Friendship status.

    def __str__(self):
        return f'{self.username} (ID: {self.id})'

    # Consider moving create_event and delete_event to views or services later
    # as model methods for complex creations/deletions can become bulky.
    def create_event(self, title, start_time, end_time, description=None, colour='grey', event_type='personal', participants_qs=None):
        event = Event.objects.create(
            Title=title,
            Creator=self,
            StartTime=start_time,
            EndTime=end_time,
            Description=description if description is not None else {}, # Default to empty dict for JSONField
            Colour=colour,
            event_type=event_type
        )
        event.Participants.add(self) # Creator is always a participant
        if participants_qs:
            event.Participants.add(*participants_qs)
        return event

    def delete_event(self, event_id):
        try:
            event = Event.objects.get(id=event_id, Creator=self) # Ensure only creator can delete
            event.delete()
            return True
        except Event.DoesNotExist:
            raise ValueError("Такого события нет или у вас нет прав на его удаление.")


class Friendship(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принято'),
        ('declined', 'Отклонено'),
        # ('blocked', 'Заблокировано') # Optional
    ]
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friendship_requests_sent', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friendship_requests_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('requester', 'receiver') # Ensures no duplicate requests
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.requester.username} to {self.receiver.username} - {self.get_status_display()}"


class Event(models.Model):
    # Define type choices clearly
    TYPE_PERSONAL = 'personal'
    TYPE_WORK = 'work'
    TYPE_SOCIAL = 'social'
    TYPE_OTHER = 'other'

    EVENT_TYPE_CHOICES = [
        (TYPE_PERSONAL, 'Личное'),
        (TYPE_WORK, 'Работа/Учеба'),
        (TYPE_SOCIAL, 'С друзьями'),
        (TYPE_OTHER, 'Другое'),
    ]
    
    # Mapping types to colors from your screenshot
    # This should be a class attribute or defined outside if used at class level for choices,
    # but for the save() method, it's fine as a class attribute.
    EVENT_COLORS = {
        TYPE_PERSONAL: '#e91e63', # Pink
        TYPE_WORK: '#2196f3',     # Blue
        TYPE_SOCIAL: '#4caf50',   # Green
        TYPE_OTHER: '#00695C',    # Dark Teal / Dark Green for "сон"
    }

    Title = models.CharField(max_length=100, blank=False, default='event')
    Creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_events')
    StartTime = models.DateTimeField(blank=False)
    EndTime = models.DateTimeField(blank=False)
    Description = models.JSONField(null=True, blank=True, default=dict)
    
    event_type = models.CharField(
        max_length=20, 
        choices=EVENT_TYPE_CHOICES, 
        default=TYPE_PERSONAL, 
        verbose_name="Тип события"
    )
    Colour = models.CharField(
        max_length=20, 
        blank=True, 
        help_text="CSS цвет (напр., #RRGGBB или teal). Будет выбран по типу события, если не указан."
    )

    Participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="events", blank=True)

    def save(self, *args, **kwargs):
        if not self.Colour and self.event_type in self.EVENT_COLORS:
            self.Colour = self.EVENT_COLORS[self.event_type]
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.Title} (ID: {self.id}) by {self.Creator.username}'


class ChatRoom(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True, help_text="Название группового чата") # For group chats
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_chat_rooms', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Создатель чата")
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms')
    is_group = models.BooleanField(default=False, verbose_name="Это групповой чат?")
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True) # To sort conversations

    def __str__(self):
        if self.name:
            return self.name
        # For 1-on-1 chats, could generate a name from participants if needed
        return f"Чат {self.id} ({self.participants.count()} участников)"

class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # is_read = models.BooleanField(default=False) # Optional for read receipts

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Сообщение от {self.sender.username} в {self.chat_room.id} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"

# To automatically create a UserProfile when a User is created:
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save() # Save profile on user update too (e.g. if User model gets new fields that affect profile)