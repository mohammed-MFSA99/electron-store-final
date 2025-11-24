from store.models import Category, Cart, Wishlist


def categories_processor(request):
    categories = Category.objects.order_by("id").all()
    return {"all_categories": categories}


def cart_context(request):
    """يجعل عدد عناصر السلة متاحاً في كل صفحات الموقع"""
    # ⚠️ إنشاء الجلسة إذا لم تكن موجودة ⚠️
    if not request.session.session_key:
        request.session.create()

    cart = request.session.get("cart", {})
    return {"cart_total_items": len(cart.values())}


def wishlist_context(request):
    """إظهار عدد عناصر المفضلة في كل الصفحات"""
    if request.user.is_authenticated:
        # حساب العدد للمستخدم المسجل
        count = Wishlist.objects.filter(user=request.user).count()
    else:
        count = 0
    return {"wishlist_count": count}


def categories_processor(request):
    # نجلب الفئات الرئيسية فقط (التي ليس لها أب)
    # ونستخدم prefetch_related لجلب الأبناء معهم دفعة واحدة (لتحسين الأداء)
    main_categories = Category.objects.filter(parent=None).prefetch_related("children")
    return {"main_categories": main_categories}
