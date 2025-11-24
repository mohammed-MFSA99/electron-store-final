from django import template

register = template.Library()


@register.inclusion_tag("partials/star_rating.html")
def show_rating(rating, num_reviews=0):
    """عرض نجوم التقييم"""
    rating = float(rating) if rating else 0
    stars = []

    for i in range(1, 6):
        if rating >= i:
            stars.append("full")
        elif rating >= i - 0.5:
            stars.append("half")
        else:
            stars.append("empty")

    return {"stars": stars, "num_reviews": num_reviews}
