# Generated migration for adding slug field to Product model

from django.db import migrations, models
from django.utils.text import slugify


def generate_slugs(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    for product in Product.objects.all():
        if not product.slug:
            base_slug = slugify(product.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            product.slug = slug
            product.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_product_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, max_length=200, null=True, unique=True),
        ),
        migrations.RunPython(generate_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(max_length=200, unique=True),
        ),
    ]
