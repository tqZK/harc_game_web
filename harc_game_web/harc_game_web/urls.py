"""
harc_game_web URL Configuration
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView, LoginView
from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required

from apps.core.views import frontpage
from apps.tasks.views import UploadView, UploadCompleteView, complete_task, check_task, TaskView
from apps.users.views import signup
from apps.posts.views import list_active_posts, list_all_posts, view_post, edit_post, new_post, delete_post
from apps.teams.views import TeamView
from apps.wotd.views import WordOfTheDayView
from apps.bank.views import BankReport

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', frontpage, name='frontpage'),
   # path('', list_active_posts, name='frontpage'),
    path('signup/', signup, name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', LoginView.as_view(template_name='users/login.html'), name='login'),

    # tasks
    path('tasks/', TaskView.as_view(), name='tasks'),
    path('complete_task/', complete_task, name='complete_task'),
    path('check_task/', check_task, name='check_task'),
    path('api_upload/', UploadView.as_view(), name='api_upload'),
    path('api_upload_complete/', UploadCompleteView.as_view(), name='api_upload_complete'),

    # Posts
    path('posts/', list_active_posts, name='all_posts'),
    path('posts/edit/', list_all_posts, name='edit_posts'),
    path('posts/view/<slug:slug>', view_post, name='view_post'),
    path('posts/new/', new_post, name='new_post'),
    path('posts/edit/<slug:slug>', edit_post, name='edit_post'),
    path('posts/delete/<slug:slug>', delete_post, name='delete_post'),

    # Teams
    path('teams/list/', TeamView.as_view(), name='all_teams'),
    path('teams/view/<slug:id>', TeamView.view, name='view_team'),

    # WordOfTheDay
    path('wotd/', WordOfTheDayView.as_view(), name='word_of_the_day'),

    # Bank & reporting
    path('report/', staff_member_required(BankReport.as_view()), name='bank_report'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
