from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from PIL import Image
import os

class HomeSlide(models.Model):
    title = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='slides/')
    order = models.PositiveIntegerField(default=0, help_text="Slide ordering")


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.image:
            return

        image_path = self.image.path

        img = Image.open(image_path)
        img = img.convert("RGB")  # Normalize PNG vs JPG differences

        # TARGET RATIO
        target_ratio = 16 / 7
        width, height = img.size
        current_ratio = width / height

        # Crop calculation
        if current_ratio > target_ratio:
            # Image too wide → cut from sides
            new_width = int(height * target_ratio)
            offset = (width - new_width) // 2
            img = img.crop((offset, 0, offset + new_width, height))
        else:
            # Image too long → cut from top-bottom
            new_height = int(width / target_ratio)
            offset = (height - new_height) // 2
            img = img.crop((0, offset, width, offset + new_height))

        # Ideal size for slider
        FINAL_WIDTH = 1920
        FINAL_HEIGHT = int(1920 * 7 / 16)  # 840px

        img = img.resize(
            (FINAL_WIDTH, FINAL_HEIGHT),
            Image.LANCZOS  #  Highest quality resize
        )

        # Overwrite with highest quality
        img.save(
            image_path,
            format="JPEG",
            quality=95,          # quality does not decrease
            optimize=True,
            progressive=True     # SEO + fast loading
        )
    def __str__(self):
        return self.title or f"Slide {self.pk}"

# 1. WHEN SLIDE IS DELETED, DELETE THE PHYSICAL IMAGE
@receiver(post_delete, sender=HomeSlide)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    When record is deleted from database, delete the physical image from disk.
    """
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)

# 2. WHEN SLIDE IS UPDATED, DELETE THE OLD IMAGE
@receiver(pre_save, sender=HomeSlide)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """
    When file is updated, delete the old file from disk.
    """
    if not instance.pk:
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).image
    except sender.DoesNotExist:
        return False

    new_file = instance.image
    if not old_file == new_file:
        if old_file and os.path.isfile(old_file.path):
            os.remove(old_file.path)