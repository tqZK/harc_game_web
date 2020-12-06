from chunked_upload.models import ChunkedUpload
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator
from apps.core.utils import calculate_week
from apps.users.models import FreeDay, HarcgameUser, Scout

ChunkedFileUpload = ChunkedUpload


class UploadedFile(models.Model):
    """
    Model załadowanego pliku
    """
    user = models.ForeignKey(HarcgameUser, on_delete=models.RESTRICT, null=True, default=None)
    file = models.FileField()
    filename_orig = models.CharField(max_length=200, null=True)
    upload_id = models.CharField(max_length=32, null=True)

    def __str__(self):
        return f"{self.file.name} - {self.filename_orig} - {self.upload_id}"


class Task(models.Model):
    """
    Model zadania
    """
    name = models.CharField("Nazwa", max_length=200)
    category = models.CharField("Kategoria", max_length=100, default='', null=True)
    description = models.TextField("Opis", max_length=400)
    allowed_completition_frequency = models.CharField("Jak często można wykonywać", max_length=200)
    prize = models.IntegerField("Nagroda", default=0, null=True)
    extra_prize = models.CharField("Nagroda specjalna", max_length=200, default=None, null=True, blank=True)

    class Meta:
        verbose_name = "zadanie"
        verbose_name_plural = "zadania"

    def can_be_completed_today(self, user):
        """
        Check if the task can be completed today
        """

        can_be_completed = True
        if self.allowed_completition_frequency == 'raz na grę':
            if DocumentedTask.objects.filter(user=user).filter(task=self):
                can_be_completed = False
        elif self.allowed_completition_frequency == 'raz w tygodniu':
            user_documented_tasks = DocumentedTask.objects.filter(user=user).filter(task=self)
            weeks_of_user_documented_tasks = []
            for task in user_documented_tasks:
                weeks_of_user_documented_tasks.append(calculate_week(task.date_completed))
            if calculate_week(timezone.now()) in weeks_of_user_documented_tasks:
                can_be_completed = False
        elif self.allowed_completition_frequency == 'raz dziennie':
            if DocumentedTask.objects.filter(user=user).filter(task=self).filter(date_completed__date=timezone.now()):
                can_be_completed = False
        else:
            # bez ograniczeń
            pass
        return can_be_completed
        
    def can_be_completed_few_times(self, task_frequency, how_many_times):
        if how_many_times != 1: 
            if task_frequency == "bez ograniczeń":
                return True
            else:
                return False
        else: 
            return True

    def __str__(self):
        return f"{self.category} | {self.name} ({self.allowed_completition_frequency})"


class DocumentedTask(models.Model):
    """
    Model udokumentowanego wykonanego zadania
    """
    task = models.ForeignKey(Task, on_delete=models.RESTRICT, null=True, default=None)
    how_many_times =  models.PositiveSmallIntegerField("Ile razy zadanie zostało wykonane", null = True, default=1, validators=[MaxValueValidator(100), MinValueValidator(1)])
    user = models.ForeignKey(HarcgameUser, on_delete=models.RESTRICT, null=True, default=None)
    date_completed = models.DateTimeField("Data ukończenia", default=timezone.now)
    date_last_edited = models.DateTimeField("Data ostatniej edycji", null=True, default=None)
    comment_from_user = models.TextField("Komentarz użytkownika", max_length=400, null=True, default="", blank=True)
    file1 = models.ForeignKey(UploadedFile, on_delete=models.RESTRICT, null=True, default=None, related_name='file1')
    file2 = models.ForeignKey(UploadedFile, on_delete=models.RESTRICT, null=True, default=None, related_name='file2')
    file3 = models.ForeignKey(UploadedFile, on_delete=models.RESTRICT, null=True, default=None, related_name='file3')
    link1 = models.URLField(max_length=400, null=True, default="", blank=True)
    link2 = models.URLField(max_length=400, null=True, default="", blank=True)
    link3 = models.URLField(max_length=400, null=True, default="", blank=True)

    class Meta:
        verbose_name = "udokumentowane zadanie"
        verbose_name_plural = "udokumentowane zadania"

    def __str__(self):
        return f'{self.task} - completed by {self.user}'


# Maybe I should have moved this to some other place?
class ModelWithChangeDetection(models.Model):
    """
    From https://gist.github.com/alican/cb9e81699e4ad1af81ca897ae500393b
    """
    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._state.adding = False
        instance._state.db = db
        instance._old_values = dict(zip(field_names, values))
        return instance

    def data_changed(self, fields):
        """
        example:
        if self.data_changed(['street', 'street_no', 'zip_code', 'city', 'country']):
            print("one of the fields changed")

        returns true if the model saved the first time and _old_values doesnt exist
                or when model saved again and data changed

        """
        if hasattr(self, '_old_values'):
            if not self.pk or not self._old_values:
                return True

            for field in fields:
                if getattr(self, field) != self._old_values[field]:
                    return True
            return False

        return True


class TaskApproval(ModelWithChangeDetection):
    """
    Model zatwierdzania zadania (jako dodatkowe atrybuty udokumentowanego wykonania zadania
    """
    documented_task = models.OneToOneField(DocumentedTask, on_delete=models.CASCADE)
    approver = models.ForeignKey(
        HarcgameUser, on_delete=models.RESTRICT, null=True, default=None
    )
    is_accepted = models.BooleanField("Zaakceptowane", default=False)
    is_closed = models.BooleanField("Zamknięte", default=False)
    comment_from_approver = models.TextField("Komentarz od akceptującego", max_length=400, default="", blank=True)

    class Meta:
        verbose_name = "akceptacja zadań"
        verbose_name_plural = "akceptacje zadań"

    def __str__(self):
        return f'{self.documented_task} - approval by {self.approver}'


class FavouriteTask(models.Model):
    """
    Model relation of favourite tasks
    """
    user = models.ForeignKey(HarcgameUser, on_delete=models.RESTRICT, null=True, default=None)
    task = models.ForeignKey(Task, on_delete=models.RESTRICT, null=True, default=None)

    class Meta:
        verbose_name = "ulubione zadanie"
        verbose_name_plural = "ulubione zadania"

    def __str__(self):
        return f"{self.user} - {self.task}"


def pick_approver(user):
    """
    Function to pick a task approver to the new task
    """
    user = Scout.objects.get(user=user)

    # get approvers that are in different team and do not have free day
    not_available_approvers = [free_day.user for free_day in FreeDay.objects.filter(day=timezone.now())]
    available_approvers = [
        t.user for t in
        Scout.objects.filter(is_team_leader=True).exclude(team=user.team).exclude(user__in=not_available_approvers)
    ]

    # pick one with least tasks to approve
    if available_approvers:
        approvers = available_approvers
    elif not_available_approvers:
        approvers = not_available_approvers
    else:
        return None

    task_approval_count = {approver.id: 0 for approver in approvers}
    for task_approval in TaskApproval.objects.filter(approver__in=approvers).values():
        task_approval_count[task_approval['approver_id']] += 1

    return HarcgameUser.objects.get(id=min(task_approval_count, key=task_approval_count.get))


@receiver(models.signals.post_save, sender=DocumentedTask)
def update_profile_signal(sender, instance, created, **kwargs):
    if created:
        TaskApproval.objects.create(
            documented_task=instance,
            approver=pick_approver(instance.user)
        )
    instance.taskapproval.save()


def close_task_approvals():
    """
    Called by cron at 00:00 on Saturday to close the task approvals
    """
    # Pick tasks, which are not closed and completed in the past and close them
    TaskApproval.objects.filter(is_closed=False).filter(is_accepted=True).exclude(documented_task__date_completed__gte=timezone.now()).update(is_closed=True)
