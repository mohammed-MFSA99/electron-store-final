from django import template

register = template.Library()


@register.filter(name="currency")
def currency(value):
    return "{:,.2f}".format(value) + " $"


register.filter("currency", currency)
