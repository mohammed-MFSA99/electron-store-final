from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("products/<int:cid>/", views.products, name="products"),
    path("products/", views.products, name="products"),
    path("product/<int:product_id>/", views.product_details, name="product_details"),
    path("checkout/", views.checkout, name="checkout"),
    path("about/", views.about, name="about"),
    path("profile/", views.profile, name="profile"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("add-review/<int:product_id>/", views.add_review, name="add_review"),
    # path("cart_update/<int:product_id>/", views.cart_update, name="cart_update"),
    # path("cart_remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("remove-from-cart/", views.remove_from_cart, name="remove_from_cart"),
    path("api/login/", views.login_ajax, name="login_ajax"),
    path("api/register/", views.register_ajax, name="register_ajax"),
    path("logout/", views.logout_view, name="logout"),
    path("api/wishlist/toggle/", views.toggle_wishlist, name="toggle_wishlist"),
    path(
        "api/wishlist/remove/", views.remove_from_wishlist, name="remove_from_wishlist"
    ),
    path(
        "api/wishlist/move-to-cart/",
        views.move_wishlist_to_cart,
        name="move_wishlist_to_cart",
    ),
    path("contact/", views.contact, name="contact"),
]
