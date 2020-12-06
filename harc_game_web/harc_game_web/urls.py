"""
harc_game_web URL Configuration
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView, LoginView
from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required

from apps.bank.views import BankReport
from apps.core.views import frontpage
from apps.posts.views import list_active_posts, list_all_posts, view_post, edit_post, new_post, delete_post
from apps.shop.views import view_shop_offers, list_active_requests, view_request, new_request, edit_request, delete_request, change_vote
from apps.tasks.scheduler import start_scheduler
from apps.tasks.views import UploadView, UploadCompleteView, add_completed_task, check_task, TaskView, \
    all_documented_tasks, list_completed_tasks, edit_completed_task, fav_task, unfav_task
from apps.teams.views import view_teams_list, view_team, view_team_details
from apps.users.views import signup, view_profile, edit_profile, change_password
from apps.wotd.views import WordOfTheDayView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', frontpage, name='frontpage'),

    path('signup/', signup, name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', LoginView.as_view(template_name='users/login.html'), name='login'),
    path('profile/view/', view_profile, name='view_profile', kwargs={'user_id': None}),
    path('profile/view/<int:user_id>', view_profile, name='view_profile'),
    path('profile/edit/<int:user_id>', edit_profile, name='edit_profile'),
    path('profile/edit/<int:user_id>/password', change_password, name='change_password'),

    # tasks
    path('tasks/', TaskView.as_view(), name='tasks', kwargs={'tab': None}),
    path('tasks/<slug:tab>', TaskView.as_view(), name='tasks'),
    path('completed_tasks/', list_completed_tasks, name='list_completed_tasks'),
    path('completed_tasks/new/', add_completed_task, name='add_completed_task', kwargs={'task_id': None}),
    path('completed_tasks/new/<slug:task_id>', add_completed_task, name='add_completed_task'),
    path('completed_tasks/edit/<slug:documented_task_id>', edit_completed_task, name='edit_completed_task'),
    path('completed_tasks/fav/<slug:id>', fav_task, name='fav_task'),
    path('completed_tasks/fav/<slug:id>/<slug:tab>', fav_task, name='fav_task'),
    path('completed_tasks/unfav/<slug:id>', unfav_task, name='unfav_task'),
    path('completed_tasks/unfav/<slug:id>/<slug:tab>', unfav_task, name='unfav_task'),
    path('check_task/', check_task, name='check_task'),
    path('all_documented_tasks/', all_documented_tasks, name='all_documented_tasks'),
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
    path('teams/list/', view_teams_list, name='all_teams'),
    path('teams/view/<slug:team_id>', view_team, name='view_team'),
    path('teams/details/<slug:team_id>', view_team_details, name='view_team_details'),

    # WordOfTheDay
    path('wotd/', WordOfTheDayView.as_view(), name='word_of_the_day'),

    # Bank & reporting
    path('report/', staff_member_required(BankReport.as_view()), name='bank_report'),

    # Shop
    path('shop/', view_shop_offers, name='shop'),

    # Requests
    path('requests/', list_active_requests, name='active_requests'),
    path('requests/view/<slug:id>', view_request, name='view_request'),
    path('requests/new/', new_request, name='new_request'),
    path('requests/edit/<slug:id>', edit_request, name='edit_request'),
    path('requests/delete/<slug:id>', delete_request, name='delete_request'),
    path('requests/vote/<slug:id>', change_vote, name='change_vote'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Launch the cron scheduler
start_scheduler()
