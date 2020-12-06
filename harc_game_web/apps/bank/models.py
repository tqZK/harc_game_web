from django.db import models
from django.dispatch import receiver
from django.utils import timezone

from apps.core.utils import calculate_week, round_half_up
from apps.tasks.models import DocumentedTask, TaskApproval
from apps.users.models import HarcgameUser, Scout


class Bank(models.Model):
    """
    Model bank zaakceptowanych taskow

    Bank
        Historia przyznawania punktów (brutto, przed podatkiem)
        Atrybuty:
            Data (dzień i godzina)
            Id gracza
            zaliczone zadanie (z zadania można wziąć nagrodę)

    """
    user = models.ForeignKey(HarcgameUser, on_delete=models.RESTRICT, null=True, default=None)
    date_accrued = models.DateTimeField(default=timezone.now)
    documented_task = models.ForeignKey(DocumentedTask, on_delete=models.RESTRICT, null=True, default=None)
    accrual = models.IntegerField(default=0, null=True)
    accrual_extra_prize = models.CharField(max_length=200, default=None, null=True, blank=True)
    # accruals are marked as deleted, bit not deleted
    accrual_deleted = models.BooleanField(default=False)
    # Allowed types of accrual (it is mainly for ledger debugging):
    # "tax" - tax taken from team member
    # "netto" - ramaining prize afer tax, used for members
    # "brutto" - whole prize, not taxed, used for team leaders
    accrual_type = models.CharField(max_length=10)
    # Additional property, which needs to be calculated here, otherwise can't be used queries
    # It will be used to display prizes grouped by weeks of year
    # Format 2020-W46
    year_week = models.CharField(max_length=8)

    REQUIRED_FIELDS = ['user', 'date_accrued', 'documented_task', 'accrual', 'accrual_type']

    @property
    def task(self):
        return self.documented_task.task

    def save(self, *args, **kwargs):
        # Calculate the year and week number
        # As we treat the week as Saturday through Friday, we need to move it by 2 days
        # As normally, the week is Monday through Sunday
        self.year_week = calculate_week(self.date_accrued)
        return super(Bank, self).save(*args, **kwargs)

    def __str__(self):
        return f"{'DELETED' if self.accrual_deleted else ''} {self.date_accrued.date()} - {self.user.nickname} - {self.task} {self.accrual} pkt + {self.accrual_extra_prize}"


@receiver(models.signals.post_save, sender=TaskApproval)
def update_taskapproval_signal(sender, instance, created, **kwargs):
    if not created and not instance.is_closed and instance.data_changed(['is_accepted']):
        # If task is accepted, we can accure it
        if instance.is_accepted:
            # If this is team leader, just assign the prize to him
            if instance.documented_task.user.scout.is_team_leader:
                Bank.objects.create(
                    user=instance.documented_task.user,
                    documented_task=instance.documented_task,
                    accrual=instance.documented_task.task.prize * instance.documented_task.how_many_times,
                    accrual_extra_prize=instance.documented_task.task.extra_prize,
                    accrual_type='brutto'
                )
            else:
                # Add price for the team member and deduct tax
                Bank.objects.create(
                    user=instance.documented_task.user,
                    documented_task=instance.documented_task,
                    accrual=round_half_up(
                        instance.documented_task.task.prize * instance.documented_task.how_many_times * (1 - instance.documented_task.user.scout.team.tax)),
                    accrual_extra_prize=instance.documented_task.task.extra_prize,
                    accrual_type='netto'
                )
                # And the tax for the team leader
                try:
                    team_leader = Scout.objects.filter(team=instance.documented_task.user.scout.team,
                                                       is_team_leader=True).first().user
                except AttributeError:
                    team_leader = None
                    raise ValueError(
                        f"{instance.documented_task.user} nie jest w żadnej drużynie lub drużyna nie ma drużynowego!"
                    )
                if team_leader:
                    Bank.objects.create(
                        user=team_leader,
                        documented_task=instance.documented_task,
                        accrual=round_half_up(
                            instance.documented_task.task.prize * instance.documented_task.how_many_times * instance.documented_task.user.scout.team.tax
                        ),
                        accrual_extra_prize=None,
                        accrual_type='tax'
                    )
        else:
            # Instead of deleting accruals, we mark them deleted, to have the prove
            Bank.objects.filter(documented_task=instance.documented_task).update(accrual_deleted=True)
    # instance.taskapproval.save()
