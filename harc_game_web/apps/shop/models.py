from django.db import models
from django.utils import timezone

from apps.users.models import HarcgameUser

CATEGORY_CHOICES = [
    ('minecraft_item', 'Przedmioty z Minecrafta'),
    ('building', 'Budynki'),
    ('other', 'Inne'),
]


"""
Harcerze powinni widzieć, co będą mogli kupić w grze za punkty zdobyte za zadania w aplikacji. Należy stworzyć podstronę (app) zawierającą aktualną ofertę.
Harcerz może również zgłosić prośbę o jakiś przedmiot poprzez formularz próśb.

Zmiany w bazie danych:

tabela z przedmiotami z Minecrafta (zewnętrzny link do ikony, nazwa angielska, nazwa polska - wszystkie dane na bazie https://minecraft.gamepedia.com/Minecraft_Wiki )
tabela z innymi rzeczami do kupienia (obrazek, nazwa, opis) (może być połączona z tabelą wyżej + dodanie "category" ?)
tabela oferty sklepu (id przedmiotu, cena, dzień)
tabela z logiem próśb (user id, prośba, proponowana cena, data) głosowanie?
Zmiany w navbarze:

"""


class Item(models.Model):
    """
    Model for items in the shop
    """
    link_image = models.CharField('Link do obrazu', max_length=400, null=True, default="", blank=True)
    name_pl = models.CharField('Nazwa polska', max_length=200, null=True, default="", blank=True)
    name_eng = models.CharField('Nazwa angielska', max_length=200, null=True, default="", blank=True)
    description = models.TextField('Opis', max_length=1000, help_text='Można używać tagów HTML')
    category = models.CharField(
        'Kategoria', max_length=100, choices=CATEGORY_CHOICES, null=True, default="other", blank=True
    )

    class Meta:
        verbose_name = "przedmiot"
        verbose_name_plural = "przedmioty"

    def __str__(self):
        return self.name_pl


class ItemOffer(models.Model):
    """
    Model for offers - items available in the shop
    """
    item = models.ForeignKey(Item, on_delete=models.RESTRICT, null=True, default=None)
    price = models.IntegerField('Cena', default=0, null=True)
    is_available = models.BooleanField('Czy dostępny', default=True, null=True)

    class Meta:
        verbose_name = "oferta przedmiotu"
        verbose_name_plural = "oferty przedmiotów"

    def __str__(self):
        return f"Offer for {self.item} - {self.price} - {self.is_available}"


class Request(models.Model):
    """
    Model prośby

    tabela z logiem próśb
    Atrybuty:
        user id (user)
        prośba (title, content)
        proponowana cena (price)
        data (date)

    (głosowanie?)
    """

    user = models.ForeignKey(HarcgameUser, on_delete=models.RESTRICT, null=True, default=None)
    title = models.CharField('Nazwa', max_length=50, default="", blank=True)
    content = models.TextField('Opis prośby', help_text='Można używać tagów HTML')
    link1 = models.URLField('Link 1', max_length=400, null=True, default="", blank=True)
    link2 = models.URLField('Link 2', max_length=400, null=True, default="", blank=True)
    link3 = models.URLField('Link 3', max_length=400, null=True, default="", blank=True)
    price = models.IntegerField('Cena', default=0, null=True)
    date = models.DateField('Na kiedy jest to potrzebne', default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "prośba"
        verbose_name_plural = "log próśb"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.title:
            # Newly created object, so set title if was not entered
            if (len(self.content) > 47):
                self.title = self.content[:47] + '...'
            else:
                self.title = self.content

            return super(Request, self).save(*args, **kwargs)
        else:
            # update
            return super(Request, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.title} - stworzona przez {self.user}'


class Vote(models.Model):
    """
    Model głosu na prośbę
    """

    user = models.ForeignKey(HarcgameUser, on_delete=models.RESTRICT, null=True, default=None)
    request = models.ForeignKey(Request, on_delete=models.RESTRICT, null=True, default=None)

    class Meta:
        verbose_name = "głos na prośbę"
        verbose_name_plural = "głosy na prośby"

    def __str__(self):
        return f"{self.user} - {self.request}"