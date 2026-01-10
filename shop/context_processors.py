from .cart import Cart

def cart_items_count(request):
    cart = Cart(request)
    return {
        'cart_items_count': cart.get_total_items(),
        'cart_subtotal': cart.get_subtotal(),
    }