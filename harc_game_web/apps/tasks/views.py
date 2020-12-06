from chunked_upload.constants import http_status, COMPLETE
from chunked_upload.exceptions import ChunkedUploadError
from chunked_upload.response import Response
from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView
from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, models
from django.forms import Select
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views import View

from apps.tasks.models import ChunkedFileUpload, DocumentedTask, TaskApproval, UploadedFile, Task, FavouriteTask


class TaskView(View):

    def get(self, request, tab=None, *args, **kwargs):
        categories = sorted(set(Task.objects.values_list('category', flat=True)))
        tasks_grouped = {}
        for category in categories:
            tasks_grouped[category] = Task.objects.filter(category=category)

        if not request.user.is_anonymous:
            favourite_tasks = [favourite_task.task for favourite_task in FavouriteTask.objects.filter(user=request.user)]
            tasks_grouped['ulubione'] = favourite_tasks
        else:
            favourite_tasks = []

        if not tab:
            tab = slugify(next(iter(categories)))

        return render(
            request, 'tasks/view.html', {
                'tasks_grouped': tasks_grouped, 'favourite_tasks': favourite_tasks, 'active_tab': tab})


class CompleteTaskForm(forms.ModelForm):
    def __init__(self, request, preselected_task_id=None, *args, **kwargs):
        # https://stackoverflow.com/questions/291945/how-do-i-filter-foreignkey-choices-in-a-django-modelform
        super(CompleteTaskForm, self).__init__(*args, **kwargs)  # populates the post

        available_tasks = Task.objects.filter(
            id__in=[task.id for task in Task.objects.all() if task.can_be_completed_today(request.user)])
        if available_tasks.count() == 0:
            messages.info(request, f"Nie ma żadnych zadań, które możesz dziś wykonać")
        fav_tasks = [fav_task.task.id for fav_task in FavouriteTask.objects.filter(user=request.user)]
        available_tasks = available_tasks.annotate(
            custom_order=models.Case(
                models.When(id=preselected_task_id, then=models.Value(0)),
                models.When(id__in=fav_tasks, then=models.Value(1)),
                default=models.Value(2),
                output_field=models.IntegerField()
            )
        ).order_by('custom_order')

        self.fields['task'].queryset = available_tasks
        if preselected_task_id:
            self.initial['task'] = get_object_or_404(Task, id=preselected_task_id)

    class Meta:
        model = DocumentedTask
        fields = ['task', 'how_many_times', 'comment_from_user', 'link1', 'link2', 'link3']
        labels = {
            "task": "Zadanie",
            "comment_from_user": "Twój komentarz",
            "link1": "Link 1",
            "link2": "Link 2",
            "link3": "Link 3",
            "how_many_times": "Ile razy wykonałeś zadanie"
        }
        widgets = {
            'task': Select(attrs={'class': 'rpgui-list'}),
        }


@login_required
@transaction.atomic
def add_completed_task(request, task_id=None):
    """
    Function to handle completing Task by Scout - render and process form
    """
    if request.method == "POST":
        form = CompleteTaskForm(request, task_id, request.POST)

        if form.is_valid():
            documented_task = form.save(commit=False)
            documented_task.user = request.user

            if documented_task.task.can_be_completed_today(request.user) and documented_task.task.can_be_completed_few_times(documented_task.task.allowed_completition_frequency, documented_task.how_many_times):
                documented_task.file1, documented_task.file2, documented_task.file3 = process_uploaded_files(request)
                documented_task.save()
                return redirect(reverse('list_completed_tasks'))
            else:
                messages.error(
                    request,
                    f"Te zadanie może być zaliczone tylko jeden {documented_task.task.allowed_completition_frequency}"
                )

    else:
        form = CompleteTaskForm(request, task_id)
    return render(request, 'tasks/add_completed_task.html', {'form': form, 'new': True})


@login_required
def list_completed_tasks(request):
    return render(request, 'tasks/list_completed_tasks.html', {
        'completed_tasks': DocumentedTask.objects.filter(user=request.user)
    })


class EditCompletedTaskForm(forms.ModelForm):
    class Meta:
        model = DocumentedTask
        fields = ['comment_from_user', 'how_many_times', 'link1', 'link2', 'link3']
        labels = {
            "comment_from_user": "Twój komentarz",
            "link1": "Link 1",
            "link2": "Link 2",
            "link3": "Link 3",
            "how_many_times": "Ile razy wykonałeś zadanie"
        }


def process_uploaded_files(request):
    # Process uploaded files
    uploaded_files = []
    for upload_id_field in ['uploaded_file_info1', 'uploaded_file_info2', 'uploaded_file_info3']:
        upload_id = request.POST[upload_id_field]
        if upload_id != '':
            file = UploadedFile.objects.filter(user=request.user, upload_id=upload_id).first()
        else:
            file = None
        uploaded_files.append(file)
    return uploaded_files[0], uploaded_files[1], uploaded_files[2]


@login_required
@transaction.atomic
def edit_completed_task(request, documented_task_id):
    documented_task = get_object_or_404(DocumentedTask, id=documented_task_id)
    # task can be edited only by use who added it and only if task is not checked already
    if request.user != documented_task.user or documented_task.taskapproval.is_accepted:
        redirect(reverse('list_completed_tasks'))

    if request.method == "POST":
        form = EditCompletedTaskForm(request.POST, instance=documented_task)
        if form.is_valid():
            file1, file2, file3 = process_uploaded_files(request)
            if file1:
                documented_task.file1 = file1
            if file2:
                documented_task.file2 = file2
            if file3:
                documented_task.file3 = file3
            documented_task.date_last_edited = timezone.now()
            documented_task.save()
            return redirect(reverse('list_completed_tasks'))
    else:
        form = EditCompletedTaskForm(instance=documented_task)

    return render(request, 'tasks/add_completed_task.html', {
        'form': form,
        'new': False,
        'documented_task_id': documented_task_id,
        'documented_task': documented_task,
        'file1': documented_task.file1,
        'file2': documented_task.file2,
        'file3': documented_task.file3,
    })


@login_required
def fav_task(request, id, tab=None):
    """
    Function to mark the Task as favourite by Scout - render and process form
    """
    task = Task.objects.get(id=id)
    if FavouriteTask.objects.filter(user=request.user, task=task).count()==0:
        FavouriteTask.objects.create(user=request.user, task=task)

    return redirect(reverse('tasks', args={tab}))


@login_required
def unfav_task(request, id, tab=None):
    """
    Function to un-mark the Task as favourite by Scout - render and process form
    """
    task = Task.objects.get(id=id)
    if FavouriteTask.objects.filter(user=request.user, task=task).count():
        FavouriteTask.objects.get(user=request.user, task=task).delete()

    return redirect(reverse('tasks', args={tab}))


def team_leader_check(user):
    return user.scout.is_team_leader


class CheckTaskForm(forms.ModelForm):
    class Meta:
        model = TaskApproval
        fields = ['documented_task', 'is_accepted', 'comment_from_approver']
        labels = {
            "is_accepted": "Czy zatwierdzasz zadanie?",
            "comment_from_approver": "Twój komentarz",
            "documented_task": ""
        }
        widgets = {
            "documented_task": forms.HiddenInput(),
            # "is_accepted": CheckboxInput(attrs={'class': 'rpgui-checkbox'}),
        }


@user_passes_test(team_leader_check)
@transaction.atomic
def check_task(request):
    if request.method == "POST":
        task = TaskApproval.objects.get(documented_task=request.POST['documented_task'])
        task.is_accepted = bool(request.POST.get('is_accepted', False))
        task.comment_from_approver = request.POST.get('comment_from_approver', '')
        task.save()

    user = request.user

    task_approvals = TaskApproval.objects.filter(approver=user).exclude(is_closed=True)
    unchecked_tasks = task_approvals.filter(is_accepted=False)
    checked_tasks = task_approvals.filter(is_accepted=True)

    unchecked_task_forms = [(task, CheckTaskForm(instance=task)) for task in unchecked_tasks]
    checked_task_forms = [(task, CheckTaskForm(instance=task)) for task in checked_tasks]

    return render(request, 'tasks/check.html', context={
        "unchecked_task_forms": unchecked_task_forms,
        "checked_task_forms": checked_task_forms,
    })


class UploadView(ChunkedUploadView, LoginRequiredMixin):
    model = ChunkedFileUpload
    field_name = 'uploaded_file'

    def get(self, request):
        return redirect(reverse('upload'))


class UploadCompleteView(ChunkedUploadCompleteView, LoginRequiredMixin):
    model = ChunkedFileUpload

    def get(self, request):
        return redirect(reverse('upload'))

    def _post(self, request, *args, **kwargs):
        upload_id = request.POST.get('upload_id')
        md5 = request.POST.get('md5')

        error_msg = None
        if self.do_md5_check:
            if not upload_id or not md5:
                error_msg = "Both 'upload_id' and 'md5' are required"
        elif not upload_id:
            error_msg = "'upload_id' is required"
        if error_msg:
            raise ChunkedUploadError(status=http_status.HTTP_400_BAD_REQUEST,
                                     detail=error_msg)

        chunked_upload = get_object_or_404(self.get_queryset(request),
                                           upload_id=upload_id)

        self.validate(request)
        self.is_valid_chunked_upload(chunked_upload)
        if self.do_md5_check:
            self.md5_check(chunked_upload, md5)

        chunked_upload.status = COMPLETE
        chunked_upload.completed_on = timezone.now()
        self._save(chunked_upload)
        self.on_completion(chunked_upload, request)

        return Response(self.get_response_data(chunked_upload, request),
                        status=http_status.HTTP_200_OK)

    def on_completion(self, chunked_upload, request):
        uploaded_file = chunked_upload.get_uploaded_file()
        UploadedFile.objects.create(
            user=request.user,
            file=uploaded_file,
            filename_orig=uploaded_file.name,
            upload_id=chunked_upload.upload_id
        )

    def get_response_data(self, chunked_upload, request):
        return {
            'filename': str(chunked_upload.filename),
            'upload_id': str(chunked_upload.upload_id),
        }


@staff_member_required
def all_documented_tasks(request):
    task_approvals = TaskApproval.objects.all()

    return render(request, 'tasks/documented_task_all_view.html', context={
        "task_approvals": task_approvals,
    })
