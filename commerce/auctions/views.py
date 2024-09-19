from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required


from .models import User, Category, Listing, Comment, Bid
from django import forms



class createForm(forms.Form):
    title = forms.CharField(label='title', max_length=64)
    description = forms.CharField(label='description', max_length=300)
    imageUrl = forms.CharField(label='imageUrl', max_length=1000)
    price = forms.FloatField(label='price')
    category = forms.CharField(label='Category', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control col-md-1'}))

    def __init__(self, *args, **kwargs):
        super(createForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field, forms.ModelChoiceField ):
                field.widget.attrs['class'] = 'form-control col-md-6'

class commentForm(forms.Form):
    comment = forms.CharField(label='Add Comment', max_length= 300, widget=forms.TextInput(attrs={'class': 'form-control'}))

def index(request):
    categories = Category.objects.all()
    currentCategory = None
    listings = Listing.objects.filter(isActive=True)

    if request.method == "POST":
        category_id = request.POST.get("category")
        if category_id:
            currentCategory = Category.objects.get(id=category_id)
            listings = listings.filter(category=currentCategory)

    return render(request, "auctions/index.html", {
        "listings": listings,
        "categories": categories,
        "currentCategory": currentCategory,
    })



def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")
    
    
@login_required(login_url="login")
def createListing(request):
    if request.method == "POST":
        form = createForm(request.POST)

        if form.is_valid():
            title = form.cleaned_data['title']
            description = form.cleaned_data['description']
            imageUrl = form.cleaned_data['imageUrl']
            price = form.cleaned_data['price']
            category_name = form.cleaned_data['category']  # El nombre de la categoría ingresada por el usuario
            currentUser = request.user

            # Verificar si la categoría ya existe
            category, created = Category.objects.get_or_create(categoryName=category_name)

            # Crear el nuevo listing
            newListing = Listing(
                title=title,
                description=description,
                imageUrl=imageUrl,
                price=float(price),
                category=category,  # Asignar la categoría (nueva o existente)
                owner=currentUser,
            )
            newListing.save()

            return HttpResponseRedirect(reverse('index'))
        else:
            return render(request, "auctions/create.html", {
                "form": form
            })       
    
    else:
        return render(request, "auctions/create.html",{
            "form": createForm()
        })

def view_listing(request, id):
    listingItem = Listing.objects.get(pk=id)
    isListingInWatchlist = request.user in listingItem.watchers.all()
    comments = listingItem.listingComments.all()
    isOwner = request.user.username == listingItem.owner.username
    max_value = max_bid(request.user, listingItem )
    if listingItem.currentBid == max_value and listingItem.isActive == False:
        return render(request, "auctions/listing.html",{
        "listingItem": listingItem,
        "isListingInWatchlist": isListingInWatchlist,
        "commentform": commentForm(),
        "comments": comments,
        "userBid": max_value,
        "isOwner": isOwner, 
        "message2": 'Congratulation you won the bid',
    })       
    else:
        return render(request, "auctions/listing.html",{
            "listingItem": listingItem,
            "isListingInWatchlist": isListingInWatchlist,
            "commentform": commentForm(),
            "comments": comments,
            "userBid": max_value,
            "isOwner": isOwner, 
            
        })

def max_bid(user, listingItem):
    if user.is_authenticated:
        userBids = user.Bidder.filter(auction=listingItem)
        max_value = None
        for bid in userBids:
            if max_value is None or bid.offer > max_value: max_value = bid.offer
        return max_value
    else:
        return None


@login_required(login_url="login")
def addwatchers(request, id):
    listingItem = Listing.objects.get(pk=id)
    currentUser = request.user
    listingItem.watchers.add(currentUser)
    return HttpResponseRedirect(reverse('listing', args=(id, )))

@login_required(login_url="login")
def removewatchers(request, id):
    listingItem = Listing.objects.get(pk=id)
    currentUser = request.user
    listingItem.watchers.remove(currentUser)
    return HttpResponseRedirect(reverse('listing', args=(id, )))

@login_required(login_url="login")
def watchlist(request):
    currentUser = request.user
    listings = currentUser.watched_listings.all()
    return render(request, "auctions/watchlist.html", {
        "listings": listings
    })

@login_required(login_url="login")
def addComment(request, id):
    commentform = commentForm(request.POST)

    if commentform.is_valid():
        comment = commentform.cleaned_data['comment']
        currentUser = request.user
        listingItem = Listing.objects.get(pk=id)
        newComment = Comment(author=currentUser, comment=comment, listing=listingItem)
        newComment.save()

        return HttpResponseRedirect(reverse('listing', args=(id, )))

@login_required(login_url="login")  
def addBid(request, id):
    listingItem = Listing.objects.get(pk=id)
    offer = float(request.POST['offer'])
    isListingInWatchlist = request.user in listingItem.watchers.all()
    comments = listingItem.listingComments.all()
    isOwner = request.user.username == listingItem.owner.username
    max_value = max_bid(request.user, listingItem )
    if is_valid(offer, listingItem):
        listingItem.currentBid = offer
        currentUser = request.user
        auction = listingItem
        newBid = Bid(
            auction=auction,
            user=currentUser,
            offer=offer,
        )
        newBid.save()
        listingItem.save()
        return render(request, "auctions/listing.html", {
            "message":"Your Bid has been Placed",
            "listingItem":listingItem,
            "isListingInWatchlist": isListingInWatchlist,
            "commentform": commentForm(),
            "comments": comments,
            "update": True,
            "userBid": max_value,
            "isOwner": isOwner,
        })
    else:
        return render(request, "auctions/listing.html", {
            "message": "Bid Amount Invalid",
            "listingItem":listingItem,
            "isListingInWatchlist": isListingInWatchlist,
            "commentform": commentForm(),
            "comments": comments,
            "update": False,
            "userBid": max_value,
            "isOwner": isOwner,
        })
        

@login_required(login_url="login")  
def categories(request):
    # Obtiene todas las categorías
    categories = Category.objects.all()
    return render(request, 'auctions/categories.html', {
        'categories': categories
    })

@login_required(login_url="login")  
def category_list(request, id):
    # Obtiene la categoría seleccionada
    category = get_object_or_404(Category, id=id)
    # Obtiene las listas activas para esa categoría
    listings = Listing.objects.filter(category=category, isActive=True)
    return render(request, 'auctions/category_list.html', {
        'category': category,
        'listings': listings
    })

def is_valid(offer, listingItem):
    if offer >= listingItem.price and (listingItem.currentBid is None or offer > listingItem.currentBid):
        return True
    else:
        return False
    
def closeAuction(request, id):
    listingItem = Listing.objects.get(pk=id)
    listingItem.isActive = False
    listingItem.save()
    isListingInWatchlist = request.user in listingItem.watchers.all()
    comments = listingItem.listingComments.all()
    isOwner = request.user.username == listingItem.owner.username
    max_value = max_bid(request.user, listingItem )
    return render(request, "auctions/listing.html", {
        "listingItem": listingItem,
        "isListingInWatchlist": isListingInWatchlist,
        "commentform": commentForm(),
        "comments": comments,
        "userBid": max_value,
        "isOwner": isOwner,
        "message2": "Auction is Closed"
    })

def openAuction(request, id):
    listingItem = Listing.objects.get(pk=id)
    listingItem.isActive = True
    listingItem.save()
    isListingInWatchlist = request.user in listingItem.watchers.all()
    comments = listingItem.listingComments.all()
    isOwner = request.user.username == listingItem.owner.username
    max_value = max_bid(request.user, listingItem )
    return render(request, "auctions/listing.html", {
        "listingItem": listingItem,
        "isListingInWatchlist": isListingInWatchlist,
        "commentform": commentForm(),
        "comments": comments,
        "userBid": max_value,
        "isOwner": isOwner, 
        "message2": "Auction is Opened"
    })