from django.shortcuts import render
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.db.models import F, Q, Count
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from apps.shop.models import Request, Vote, CATEGORY_CHOICES, ItemOffer

# Number of votes one user can have
MAX_VOTES = 5

"""
Harcerze powinni widzieć, co będą mogli kupić w grze za punkty zdobyte za zadania w aplikacji. Należy stworzyć podstronę (app) zawierającą aktualną ofertę.
Harcerz może również zgłosić prośbę o jakiś przedmiot poprzez formularz próśb.

Podstrona oferty sklepu (mogą być 2 widoki albo 1 - do przemyślenia/sprawdzenia)

subnavbar
widoki:
-- tabela z aktualnymi ofertami
-- prosty formularz próśb z wyświetlaniem próśb poniżej
"""


def view_shop_offers(request):
    """
    Function to list all posts
    """
    offers_available = ItemOffer.objects.filter(is_available=True)
    offers_grouped = {}
    for category_search, category_name in CATEGORY_CHOICES:
        offers_grouped[category_name] = offers_available.filter(item__category=category_search)

    return render(request, 'shop/view_shop.html', {'offers_grouped': offers_grouped})


# Requests

class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['title', 'content', 'link1', 'link2', 'link3', 'price', 'date']

    def __init__(self, *args, **kwargs):
        super(RequestForm, self).__init__(*args, **kwargs) # Call to ModelForm constructor
        #self.fields['content'].widget.attrs['cols'] = 10
        self.fields['content'].widget.attrs.update({'style':'height:50%'})


def list_active_requests(request):
    """
    Function to list all requests
    """
    requests = Request.objects.exclude(is_active=False) \
            .annotate(votes=Count('vote')) \
            .order_by(F('date').desc(nulls_last=True)
        )
    if not request.user.is_anonymous:
        requests = requests.annotate(users_vote=Count('vote', filter=Q(vote__user=request.user)))

    return render(request, 'shop/list_active_requests.html', {'requests': requests, 'max_votes': MAX_VOTES})


def view_request(request, id):
    """
    Function to list a single request
    """
    req = get_object_or_404(Request, id=id)
    votes = Vote.objects.filter(request=req).count()
    if not request.user.is_anonymous:
        users_vote = Vote.objects.filter(request=req, user=request.user).count()
    else:
        users_vote = False
    return render(request, 'shop/view_request.html', {
            'req': req, 'votes': votes, 'users_vote': users_vote,
            'edit': req.is_active and (req.user.id is request.user.id),
            'delete': req.is_active and (req.user.id is request.user.id)
        })


@login_required
def new_request(request):
    """
    Function create a request
    """

    # If request is POST, create a bound form (form with data)
    if request.method == "POST":
        form = RequestForm(request.POST)

        # check whether form is valid or not
        # if the form is valid, save the data to the database
        # and redirect the user back to the add request form

        # If form is invalid show form with errors again
        if form.is_valid():
            #  save data
            req = form.save()
            req.user = request.user
            req.save()
            return redirect('view_request', id=req.id)
    # if request is GET the show unbound form to the user
    else:
        form = RequestForm()
    return render(request, 'shop/edit_request.html', {'form': form})


@login_required
def edit_request(request, id):
    """
    Function edit a request
    """
    req = get_object_or_404(Request, id=id)
    if not req.is_active:
        messages.error(request,"Prośba została już zrealizowana")
        return redirect(reverse('view_request', args=[req.id]))

    if req.user.id is not request.user.id:
        messages.error(request,f"Prośba może być edytowana tylko przez {req.user.scout}")
        return redirect(reverse('view_request', args=[req.id]))

    # If request is POST, create a bound form(form with data)
    if request.method == "POST":
        form = RequestForm(request.POST, instance=req)

        # check whether form is valid or not
        # if the form is valid, save the data to the database
        # and redirect the user back to the update request form

        # If form is invalid show form with errors again
        if form.is_valid():
            form.save()
            return redirect(reverse('view_request', args=[req.id]))

    # if request is GET the show unbound form to the user, along with data
    else:
        form = RequestForm(instance=req)

    return render(request, 'shop/edit_request.html', {'form': form})


@login_required
def delete_request(request, id):
    """
    Function to delete a request
    """
    req = get_object_or_404(Request, id=id)
    if not req.is_active:
        messages.error(request,"Prośba została już zrealizowana")
    elif req.user.id is not request.user.id:
        messages.error(request,f"Prośba może być usunięta tylko przez {req.user.scout}")
    else:
        req.delete()

    return redirect(reverse('active_requests'))


# Votes

def can_vote(user):
    return Vote.objects.filter(user=user).count() < MAX_VOTES


@login_required
def change_vote(request, id):
    try:
        vote = Vote.objects.get(user=request.user, request__id=id)
    except ObjectDoesNotExist:
        if can_vote(request.user):
            Vote.objects.create(user=request.user, request=get_object_or_404(Request, id=id))
        else:
            messages.error(request,f"Możesz oddać tylko {MAX_VOTES} głosów")

    else:
        vote.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
#    return redirect(reverse('active_requests'))