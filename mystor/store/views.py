from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import json
import urllib.parse
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.db.models import Q, Avg, Count
from django.db.models.functions import Coalesce
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Product, Category, Customer, Review, Wishlist


# ==========================================
# 1. الصفحات الرئيسية (Main Pages)
# ==========================================


def index(request):
    products = (
        Product.objects.select_related("category")
        .filter(stock__gt=0)
        .order_by("-id")[:4]
        .annotate(avg_rating=Avg("reviews__rating"), num_reviews=Count("reviews"))
    )
    return render(
        request,
        "index.html",
        {
            "products": products,
            "categories": Category.objects.all(),
        },
    )


def about(request):
    return render(request, "about.html")


def contact(request):
    breadcrumbs = [
        {"title": "الرئيسية", "url": reverse("index")},
        {"title": "تواصل معنا", "url": None},
    ]
    return render(request, "contact.html", {"breadcrumbs": breadcrumbs})


def products(request, cid=None):
    # استقبال المتغيرات
    search_query = request.GET.get("q", "")
    sort_by = request.GET.get("sort", "newest")
    cid_param = request.GET.get("cid")

    # القائمة الأساسية
    products_list = Product.objects.all()

    # الفلترة حسب الفئة
    category_obj = None
    if cid:
        category_obj = get_object_or_404(Category, pk=cid)
        products_list = products_list.filter(category=category_obj)
    elif cid_param:
        category_obj = get_object_or_404(Category, pk=cid_param)
        products_list = products_list.filter(category=category_obj)

    # البحث
    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__name__icontains=search_query)
        ).distinct()

    # الترتيب
    if sort_by == "price_asc":
        products_list = products_list.order_by("price")
    elif sort_by == "price_desc":
        products_list = products_list.order_by("-price")
    elif sort_by == "rating":
        products_list = products_list.annotate(
            avg_rating=Coalesce(Avg("reviews__rating"), 0.0)
        ).order_by("-avg_rating", "-id")
    else:
        products_list = products_list.order_by("-id")

    # الترقيم
    paginator = Paginator(products_list, 3)
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)

    breadcrumbs = [
        {"title": "الرئيسية", "url": reverse("index")},
        {"title": "المنتجات", "url": reverse("products")},
    ]

    if category_obj:
        breadcrumbs.append({"title": category_obj.name, "url": ""})
    elif search_query:
        breadcrumbs.append({"title": f'بحث: "{search_query}"', "url": ""})
    else:
        breadcrumbs.append({"title": "كل المنتجات", "url": ""})

    context = {
        "products": products,
        "current_category": category_obj,
        "breadcrumbs": breadcrumbs,
        "all_categories": Category.objects.all(),
        "search_query": search_query,
        "sort_by": sort_by,
    }
    return render(request, "products.html", context)


def product_details(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.select_related("customer").order_by("-review_date")
    review_summary = product.reviews.aggregate(
        avg_rating=Avg("rating"), num_reviews=Count("id")
    )

    related_products = Product.objects.filter(category=product.category).exclude(
        id=product.id
    )[:4]

    breadcrumbs = [
        {"title": "الرئيسية", "url": reverse("index")},
        {"title": "المنتجات", "url": reverse("products")},
        {"title": product.name, "url": None},
    ]

    context = {
        "product": product,
        "breadcrumbs": breadcrumbs,
        "reviews": reviews,
        "related_products": related_products,
        "review_summary": review_summary,
    }
    return render(request, "product_details.html", context)


# ==========================================
# 2. نظام السلة (Cart System) - النسخة المستقرة
# ==========================================


def add_to_cart(request):
    """إضافة منتج للسلة (مع إجبار الحفظ)"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = str(data.get("product_id"))
            quantity = int(data.get("quantity", 1))

            print(f"🔵 محاولة إضافة: ID={product_id}, Qty={quantity}")

            product = get_object_or_404(Product, id=product_id)

            # جلب أو إنشاء السلة
            if not request.session.session_key:
                request.session.create()

            cart = request.session.get("cart", {})

            # منطق التحديث
            if product_id in cart:
                cart[product_id] += quantity
            else:
                cart[product_id] = quantity

            # الحفظ الإجباري
            request.session["cart"] = cart
            request.session.modified = True
            request.session.save()  # مهم جداً

            print(f"✅ تم الحفظ في السلة: {cart}")

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"تم إضافة {product.name}",
                    "total_items": len(cart.values()),
                }
            )

        except Exception as e:

            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})


def remove_from_cart(request):
    """حذف منتج من السلة"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = str(data.get("product_id"))

            cart = request.session.get("cart", {})

            if product_id in cart:
                del cart[product_id]
                request.session["cart"] = cart
                request.session.modified = True
                request.session.save()

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "تم حذف المنتج",
                        "total_items": len(cart.values()),
                    }
                )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})


def checkout(request):
    """عرض صفحة السلة"""
    cart = request.session.get("cart", {})

    cart_items = []
    total_price = 0

    # تحويل المفاتيح لأرقام للبحث في القاعدة
    valid_ids = []
    for key in cart.keys():
        if str(key).isdigit():
            valid_ids.append(int(key))

    # جلب المنتجات
    products = Product.objects.filter(id__in=valid_ids)

    # المطابقة
    for product in products:
        # نحاول جلب الكمية سواء كان المفتاح نصاً أو رقماً
        quantity = cart.get(str(product.id)) or cart.get(product.id)

        if quantity:
            quantity = int(quantity)
            total = product.price * quantity
            total_price += total

            cart_items.append(
                {"product": product, "quantity": quantity, "total": total}
            )

    # واتساب
    message = "مرحباً، أرغب في طلب المنتجات التالية:\n"
    for item in cart_items:
        message += f"- {item['product'].name} (العدد: {item['quantity']})\n"
    message += f"\nالمجموع: ${total_price}"
    encoded_message = urllib.parse.quote(message)

    breadcrumbs = [
        {"title": "الرئيسية", "url": reverse("index")},
        {"title": "السلة", "url": None},
    ]
    suggested_products = Product.objects.filter(stock__gt=0).order_by("-id")[:4]

    context = {
        "cart_items": cart_items,
        "total_price": total_price,
        "breadcrumbs": breadcrumbs,
        "suggested_products": suggested_products,
        "whatsapp_message": encoded_message,
    }
    return render(request, "checkout.html", context)


# ==========================================
# 3. المصادقة (Authentication)
# ==========================================
def login_ajax(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            login_input = data.get("email")
            password = data.get("password")

            if not login_input or not password:
                return JsonResponse({"status": "error", "message": "البيانات ناقصة"})

            user = None
            if "@" in login_input:
                try:
                    u = User.objects.get(email__iexact=login_input)
                    user = authenticate(request, username=u.username, password=password)
                except User.DoesNotExist:
                    pass

            if user is None:
                user = authenticate(request, username=login_input, password=password)

            if user:
                login(request, user)
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"مرحباً {user.first_name or user.username}",
                    }
                )
            else:
                return JsonResponse({"status": "error", "message": "بيانات خاطئة"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})


def register_ajax(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("password")
            full_name = data.get("fullName", "")
            phone = data.get("phone", "")

            if User.objects.filter(email=email).exists():
                return JsonResponse(
                    {"status": "error", "message": "البريد موجود مسبقاً"}
                )

            user = User.objects.create_user(
                username=email, email=email, password=password
            )

            names = full_name.split()
            if names:
                user.first_name = names[0]
                user.last_name = " ".join(names[1:]) if len(names) > 1 else ""
            user.save()

            # إنشاء العميل
            # نعتمد على الـ Signal أو ننشئه يدوياً هنا
            Customer.objects.get_or_create(
                user=user,
                defaults={"name": full_name, "email": email, "phone_number": phone},
            )

            login(request, user)
            return JsonResponse({"status": "success", "message": "تم إنشاء الحساب"})
        except Exception as e:
            print(e)
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})


def logout_view(request):
    logout(request)
    return JsonResponse({"status": "success", "message": "تم الخروج"})


@login_required
def profile(request):

    # التأكد من وجود ملف العميل
    if hasattr(request.user, "customer_profile"):
        customer = request.user.customer_profile
    else:
        customer = Customer.objects.create(
            user=request.user,
            name=request.user.first_name or request.user.username,
            email=request.user.email,
        )

    if request.method == "POST":
        # ✅ الحالة 1: تغيير كلمة المرور
        if "old_password" in request.POST:
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                # هذا السطر مهم جداً لكي لا يتم تسجيل خروج المستخدم بعد التغيير
                update_session_auth_hash(request, user)
                return JsonResponse(
                    {"status": "success", "message": "تم تغيير كلمة المرور بنجاح!"}
                )
            else:
                # إرسال أول خطأ يظهر (مثل: كلمة المرور الحالية غير صحيحة)
                first_error = list(form.errors.values())[0][0]
                return JsonResponse({"status": "error", "message": first_error})

        # ✅ الحالة 2: تحديث البيانات الشخصية (الكود السابق)
        else:
            try:
                customer.name = request.POST.get("fullName")
                customer.phone_number = request.POST.get("phone")
                if "avatar" in request.FILES:
                    customer.avatar = request.FILES["avatar"]
                customer.save()
                return JsonResponse(
                    {"status": "success", "message": "تم تحديث الملف الشخصي"}
                )
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)})

    # إضافة: جلب عناصر المفضلة
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        "product", "product__category"
    )

    # حساب إجمالي سعر المفضلة (للعرض فقط)
    wishlist_total = sum(item.product.price for item in wishlist_items)

    breadcrumbs = [
        {"title": "الرئيسية", "url": reverse("index")},
        {"title": "الملف الشخصي", "url": None},
    ]

    context = {
        "breadcrumbs": breadcrumbs,
        "customer": customer,
        "wishlist_items": wishlist_items,
        "wishlist_total": wishlist_total,
    }

    return render(request, "profile.html", context)


# ==========================================
# 4. التقييمات (Reviews)
# ==========================================
def add_review(request, product_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            rating = int(data.get("rating"))
            comment = data.get("comment", "")
            name = data.get("name", "Guest")

            product = get_object_or_404(Product, id=product_id)

            # البحث عن عميل موجود أو إنشاء جديد
            customer, _ = Customer.objects.get_or_create(name=name)

            new_review = Review.objects.create(
                product=product, customer=customer, rating=rating, comment=comment
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "تم إضافة التقييم",
                    "review": {
                        "customer_name": customer.name,
                        "rating": rating,
                        "comment": comment,
                        "review_date": new_review.review_date.strftime("%d %b, %Y"),
                    },
                }
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})


# 1. دالة تبديل المفضلة (تستخدم للأزرار في الكروت)
@login_required
def toggle_wishlist(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = data.get("product_id")
            product = get_object_or_404(Product, id=product_id)

            exists = Wishlist.objects.filter(
                user=request.user, product=product
            ).exists()

            if exists:
                return JsonResponse(
                    {
                        "status": "exists",
                        "message": "هذا المنتج موجود بالفعل في قائمة مفضلاتك",
                    }
                )
            else:
                Wishlist.objects.create(user=request.user, product=product)
                return JsonResponse(
                    {"status": "added", "message": "تمت الإضافة للمفضلة بنجاح"}
                )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})


# 2. دالة حذف عنصر من صفحة البروفايل
@login_required
def remove_from_wishlist(request):
    if request.method == "POST":
        data = json.loads(request.body)
        product_id = data.get("product_id")
        Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
        return JsonResponse({"status": "success", "message": "تم حذف المنتج"})
    return JsonResponse({"status": "error"})


# 3. دالة نقل المفضلة إلى السلة
@login_required
def move_wishlist_to_cart(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)

    # التعامل مع السلة (Session)
    if not request.session.session_key:
        request.session.create()
    cart = request.session.get("cart", {})

    items_moved_count = 0
    for item in wishlist_items:
        pid = str(item.product.id)
        if pid in cart:
            cart[pid] += 1
        else:
            cart[pid] = 1
        items_moved_count += 1

    # حفظ السلة
    request.session["cart"] = cart
    request.session.modified = True

    # حذف العناصر من المفضلة بعد النقل (اختياري، يفضل حذفها)
    wishlist_items.delete()

    return JsonResponse(
        {
            "status": "success",
            "message": f"تم نقل {items_moved_count} منتج إلى السلة",
            "total_items": len(cart.values()),
        }
    )
