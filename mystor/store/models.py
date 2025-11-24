from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


class Category(models.Model):
    # جعل الصورة اختيارية لحل مشكلة 'NOT NULL constraint failed'
    name = models.CharField("اسم الصنف", max_length=255, unique=True)
    description = models.TextField("الوصف", blank=True, null=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children', 
        verbose_name="القسم الرئيسي"
    )
    class Meta:
        verbose_name = "الصنف"
        verbose_name_plural = "الأصناف"

    def __str__(self):
            # إذا كان له أب، يعرض: الرئيسي -> الفرعي
            if self.parent:
                return f"{self.parent.name} -> {self.name}"
            return self.name

# ---


class Brand(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "الشركة"
        verbose_name_plural = "الشركات المصنعة"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField("اسم المنتج", max_length=255)
    price = models.DecimalField("السعر", max_digits=10, decimal_places=2)
    description = models.TextField("الوصف")
    # جعل صورة المنتج اختيارية
    image = models.ImageField(
        "صورة المنتج", upload_to="products/", blank=True, null=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name="الصنف",
        related_name="products",  # إضافة related_name لتسهيل الاستعلامات
    )
    stock = models.IntegerField(
        "الكمية في المخزون", default=0, validators=[MinValueValidator(0)]
    )

    features = models.JSONField(
        blank=True,
        null=True,
        help_text='أدخل المميزات كقائمة JSON، مثال: [{"icon": "fa-microchip", "text": "معالج قوي"}]',
    )

    is_available = models.BooleanField(default=True)
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text="رقم المنتج الفريد (SKU)",
    )

    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        """
        يحسب ويعيد متوسط تقييم المنتج.
        يعيد 0.0 إذا لم يكن هناك تقييمات.
        """
        # .aggregate() تعيد قاموسًا، لذلك يجب أن نحصل على القيمة منه
        reviews_summary = self.reviews.aggregate(average=Avg("rating"))
        avg = reviews_summary.get("average", 0.0)
        # التأكد من أن القيمة ليست None
        if avg is None:
            return 0.0
        return avg

    @property
    def reviews_count(self):
        """
        يحسب ويعيد العدد الإجمالي لتقييمات المنتج.
        """
        return self.reviews.count()


# ---
class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "user",
            "product",
        )  # لمنع تكرار نفس المنتج في المفضلة لنفس المستخدم

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class Customer(models.Model):
    # ربط العميل بالمستخدم الافتراضي (علاقة واحد لواحد)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="customer_profile",
    )

    # البيانات الإضافية التي لا يوفرها User الافتراضي
    name = models.CharField("الاسم الكامل", max_length=255)
    email = models.EmailField("البريد الإلكتروني", null=True, blank=True)
    phone_number = models.CharField(
        "رقم الهاتف", max_length=20, blank=True, null=True
    )  # إضافة رقم الهاتف
    address = models.TextField("العنوان", blank=True, null=True)
    avatar = models.ImageField(
        "الصورة الشخصية", upload_to="customers/", blank=True, null=True
    )  # إضافة الصورة

    def __str__(self):
        return self.name


# --- Signals (مهم جداً) ---
# كود يقوم بإنشاء Customer تلقائياً بمجرد تسجيل مستخدم جديد في لوحة التحكم أو الموقع
@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        Customer.objects.create(
            user=instance,
            name=f"{instance.first_name} {instance.last_name}",
            email=instance.email,
        )


@receiver(post_save, sender=User)
def save_customer_profile(sender, instance, **kwargs):
    try:
        instance.customer_profile.save()
    except:
        pass


# -----------------------------------------------------------------------------
# 2. مودلات الطلبات والدفع
# -----------------------------------------------------------------------------


class Order(models.Model):
    # خيارات حالة الطلب
    STATUS_CHOICES = [
        ("PENDING", "قيد الانتظار"),
        ("PROCESSING", "قيد المعالجة"),
        ("COMPLETED", "مكتمل"),
        ("CANCELLED", "ملغي"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,  # أفضل من CASCADE هنا للاحتفاظ بسجل الطلبات
        null=True,
        verbose_name="العميل",
    )
    order_date = models.DateTimeField("تاريخ الطلب", auto_now_add=True)
    total = models.DecimalField(
        "المجموع الإجمالي", max_digits=10, decimal_places=2, default=0.00
    )
    status = models.CharField(
        "حالة الطلب", max_length=50, choices=STATUS_CHOICES, default="PENDING"
    )

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"

    def __str__(self):
        return f"طلب رقم #{self.id} للعميل {self.customer.name if self.customer else 'محذوف'}"


# ---


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, related_name="items", on_delete=models.CASCADE, verbose_name="الطلب"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, verbose_name="المنتج"
    )
    quantity = models.PositiveIntegerField("الكمية", default=1)
    price = models.DecimalField("السعر عند الشراء", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "عنصر في الطلب"
        verbose_name_plural = "عناصر الطلبات"

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


# ---


class Payment(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, verbose_name="الطلب", related_name="payment"
    )  # OneToOne أفضل
    payment_method = models.CharField("طريقة الدفع", max_length=255)
    amount = models.DecimalField("المبلغ المدفوع", max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField("تاريخ الدفع", auto_now_add=True)
    status = models.CharField("حالة الدفع", max_length=50, default="succeeded")

    class Meta:
        verbose_name = "دفعة"
        verbose_name_plural = "الدفعات"

    def __str__(self):
        return f"دفعة للطلب رقم #{self.order.id} بقيمة {self.amount}"


# -----------------------------------------------------------------------------
# 3. مودلات المراجعات والمخزون
# -----------------------------------------------------------------------------


class Review(models.Model):
    product = models.ForeignKey(
        Product, related_name="reviews", on_delete=models.CASCADE, verbose_name="المنتج"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, verbose_name="العميل"
    )
    rating = models.IntegerField(
        "التقييم",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],  # ضمان أن التقييم من 1 إلى 5
    )
    comment = models.TextField("التعليق", blank=True, null=True)
    review_date = models.DateTimeField("تاريخ المراجعة", auto_now_add=True)

    class Meta:
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"
        unique_together = ("product", "customer")  # ضمان تقييم واحد لكل عميل ومنتج

    def __str__(self):
        return f"تقييم {self.rating} نجوم للمنتج {self.product.name}"


class Cart(models.Model):
    items = models.JSONField(default=dict)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)


# ---


class Specification(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="specifications",
        on_delete=models.CASCADE,
        verbose_name="المنتج",
    )
    name = models.CharField("اسم المواصفة", max_length=255)
    value = models.CharField("قيمة المواصفة", max_length=255)

    class Meta:
        verbose_name = "الوصف"
        verbose_name_plural = "المواصفات"

    def __str__(self):
        return f"{self.name}: {self.value}"


# ---


class InventoryMovement(models.Model):
    # خيارات نوع الحركة
    MOVEMENT_CHOICES = [
        ("ADD", "إضافة"),
        ("REMOVE", "إزالة"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, verbose_name="المنتج"
    )
    quantity = models.IntegerField("الكمية المحرّكة")
    # استخدام خيارات ثابتة بدلًا من نص مفتوح
    movement_type = models.CharField(
        "نوع الحركة", max_length=10, choices=MOVEMENT_CHOICES
    )
    movement_date = models.DateTimeField("تاريخ الحركة", auto_now_add=True)

    class Meta:
        verbose_name = "حركة مخزون"
        verbose_name_plural = "المخزون"

    def __str__(self):
        return f"{self.movement_type} {self.quantity} من {self.product.name}"
