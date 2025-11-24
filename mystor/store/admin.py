from django.contrib import admin
from . import models


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_per_page = 50
    search_fields = ["name"]


@admin.register(models.Brand)
class BrandAdmin(admin.ModelAdmin):
    list_per_page = 50
    search_fields = ["name"]


@admin.register(models.Review)
class RivewAdmin(admin.ModelAdmin):
    list_per_page = 50
    search_fields = ["name"]


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_per_page = 50
    search_fields = ["name"]


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_per_page = 50


@admin.register(models.Specification)
class SpecificationAdmin(admin.ModelAdmin):
    list_per_page = 50


@admin.register(models.InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_per_page = 50
