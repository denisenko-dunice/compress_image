import sys

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from io import BytesIO
from PIL import Image


def compress_image(img_file,
                   max_dims=(1200, 1200),
                   file_desc=''):
    """
    Scales & compresses image.
    Scales an image file down if either dimension exceeds the maximum
    dimensions set.
    All images are converted/saved as a slightly compressed JPG.
    """
    img = Image.open(img_file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    width, height = img.size
    max_width, max_height = max_dims
    # Create thumbnail with same aspect ratio
    if width > max_width or height > max_height:
        img.thumbnail(max_dims, Image.ANTIALIAS)
    output = BytesIO()
    img.save(output, format='JPEG', quality=55, optimize=True)
    output.seek(0)  # Change stream position to byte 0
    return InMemoryUploadedFile(
        output,
        'ImageField',
        f'{img_file.name.split(".")[0]}{file_desc}.jpg',
        'image/jpeg',
        sys.getsizeof(output),
        None
    )


def get_comprssed_field_name(image_field_name, dimenssion):
    """Returns field name of compressed image, based on base field name and dimenssion"""
    return f'{image_field_name}_{dimenssion}'


def get_compressed_image_mixin(image_field_name, COMPRESSED_IMAGE_DIMENSSIONS=(75, 130, 604)):
    """
        Creates model mixin based on image field name, which adds compressed iamge fields.
        Compresses image each time when image its updating.
        Example usage: `
            class EventGallery(get_compressed_image_mixin('image'), (80, 130)):
                ...
                image = models.ImageField(upload_to='event_gallery/')
                ...
        `
        It will create fields for model image_80 and image_130
    """
    class CompressedImageMixin(models.Model):
        class Meta:
            abstract = True
        # Dynamic adding fields to mixin
        for dimenssion in COMPRESSED_IMAGE_DIMENSSIONS:
            image_compressed_field_name = get_comprssed_field_name(image_field_name, dimenssion)
            vars()[image_compressed_field_name] =  models.ImageField(upload_to='compressed_images/', null=True, blank=True)
        def save(self, *args, **kwargs):
            compress_images = False
            image = getattr(self, image_field_name, None)
            # Instance wasn't created before, should convert all images
            if self.id is None:
                compress_images = True
            else:
                old_instance = self.__class__.objects.get(id=self.id)
                # Compress images if image is updated
                compress_images = image != getattr(old_instance, image_field_name)
            if compress_images:
                for dimenssion in COMPRESSED_IMAGE_DIMENSSIONS:
                    image_compressed_field_name = get_comprssed_field_name(image_field_name, dimenssion)
                    # If image is none, set fields to none
                    if bool(image) is False:
                        setattr(self, image_compressed_field_name, None)
                    else:
                        # Compressing
                        image_compressed = compress_image(image, (dimenssion, dimenssion))
                        setattr(self, image_compressed_field_name, image_compressed)
            return super().save(*args, **kwargs)
    return CompressedImageMixin
