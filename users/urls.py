from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.UserListView.as_view(), name='user_list'),
    path('create/', views.UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('preferences/', views.PreferencesView.as_view(), name='preferences'),
    path('preferences/update/', views.update_preferences, name='update_preferences'),
]
