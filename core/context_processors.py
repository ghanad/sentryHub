def notifications(request):
    """
    Context processor for passing Django messages to JavaScript notifications.
    """
    from django.contrib.messages import get_messages
    
    messages_list = []
    for message in get_messages(request):
        messages_list.append({
            'level': message.level_tag,
            'message': str(message),
            'extra_tags': message.extra_tags
        })
    
    return {'django_messages': messages_list} 